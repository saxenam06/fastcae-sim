"""Write the example contracts (CON-1's checks), every value with its source.

    uv run python checks/data/contracts/make_examples.py

Three contracts:
    hofstetter2018_posed.json         package style, from Hofstetter et al. 2018 (Tables 2 and 3)
    agri_ev_gearbox_posed.json        gear-train style, from Kim et al. 2024 (Tables 1 and 3)
    textbook_two_bearing_derived.json derived stage: one gear between two bearings (GHE §6.2)

Every value is published (with its table), standard (with its clause), the engineer's (who and
when), or an assumption listed in the contract. Nothing comes from GRC. The tables were re-read
from the papers' PDFs on 8 October 2026 (pypdf), not from summaries.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).parent

HOF = "Hofstetter et al. 2018, Forsch Ingenieurwes 82:361-370"
KIM = "Kim et al. 2024, Sci Rep 14:4145, doi 10.1038/s41598-024-54606-8"
SON20 = "Son et al. 2020, Appl Sci 10:8414, doi 10.3390/app10238414"
NADCA = "NADCA Product Specification Standards for Die Castings 2015, Section 4A"
SHIGLEY = "Shigley, Mechanical Engineering Design, Table 7-2 (rough guideline)"
MARANO = "Marano et al. 2021, Gear Technology Jan-Feb 2021 (orders at least 3 % apart)"
MARGIN = (
    "Gutierrez Santiago et al. 2023 and FZG 2022 (model to test 10-25 %), via fastcae research "
    "2026-10-06-gearbox-housing-engineering.md §4"
)
ISO15 = "ISO 15 boundary dimensions, as maker catalogues list them (to check against a catalogue)"
GHE = (
    "fastcae research 2026-10-06-gearbox-housing-engineering.md §6.2, worked example on JTEKT "
    "eq. 5-29 (the report's own arithmetic, tagged Inferred)"
)
D7 = "plan D7 (least member): 4 mm, set by the FE budget on the 8 GB card"


def qty(value, unit):
    return {"value": value, "unit": unit}


def vec(x, y, z, unit):
    return {"values": [x, y, z], "unit": unit}


def entry(value, provenance, kind="hard", authority="engineer_locked"):
    return {"value": value, "provenance": provenance, "authority": authority, "kind": kind}


def pub(value, citation, note=None):
    p = {"kind": "published", "citation": citation}
    if note:
        p["note"] = note
    return entry(value, p)


def std(value, citation, note=None):
    p = {"kind": "standard", "citation": citation}
    if note:
        p["note"] = note
    return entry(value, p)


def asm(value, assumption_id):
    return entry(value, {"kind": "assumption", "assumption_id": assumption_id})


def engineer(value, who, when, note):
    return entry(value, {"kind": "engineer", "who": who, "when": when, "note": note})


def stamp(tool, version, inputs: str):
    digest = hashlib.sha256(inputs.encode("utf-8")).hexdigest()
    return {
        "kind": "derived",
        "tool": tool,
        "tool_version": version,
        "input_hash": f"sha256:{digest}",
    }


def drv(value, provenance):
    return entry(value, provenance, kind="derived")


def torque(shaft, kind, direction, value):
    return {"shaft": shaft, "kind": kind, "direction": direction, "torque": value}


def assumption(aid, what, value, why, varied=True):
    return {"id": aid, "what": what, "value": value, "why": why, "varied": varied}


def limits(check_speeds):
    return {
        "verdict_rule_version": "v0.1",
        "mesh_misalignment_share": asm(qty(50, "%"), "A6"),
        "centre_distance_share": asm(qty(50, "%"), "A6"),
        "ovalisation_share": asm(qty(50, "%"), "A6"),
        "bearing_tilt": [
            {
                "bearing_type": "tapered_roller",
                "limit": std(qty(0.5, "mrad"), SHIGLEY, "lower end of 0.5-1.2 mrad"),
            },
            {
                "bearing_type": "cylindrical_roller",
                "limit": std(qty(0.8, "mrad"), SHIGLEY, "lower end of 0.8-1.2 mrad"),
            },
            {
                "bearing_type": "deep_groove_ball",
                "limit": std(qty(1.0, "mrad"), SHIGLEY, "lower end of 1-3 mrad"),
            },
        ],
        "order_separation": pub(qty(3, "%"), MARANO),
        "order_check_speeds": check_speeds,
        "model_margin": pub(qty(25, "%"), MARGIN, "the top of the measured range"),
        "objective": "least_mass",
        "stress": "recorded",
    }


def manufacturing(pull):
    card = f"{KIM}, Table 3, housing LH"
    return {
        "process": "high_pressure_die_casting",
        "pull_directions": pull,
        "draft_inside": std(qty(2, "deg"), NADCA, "inside surfaces, features at least 1 in deep"),
        "draft_outside": std(qty(1, "deg"), NADCA, "outside surfaces, features at least 1 in deep"),
        "draft_min_depth": std(qty(25.4, "mm"), NADCA),
        "min_wall": engineer(qty(4, "mm"), "the engineer", "2026-10-07 11:41", D7),
        "machining_stock": std(qty(0.25, "mm"), NADCA, "normal minimum machining allowance"),
        "material": {
            "name": "aluminium housing card (Kim et al. 2024, Table 3, housing LH)",
            "youngs_modulus": pub(qty(70.93, "GPa"), card),
            "poisson_ratio": pub(qty(0.3135, "1"), card),
            "density": pub(qty(2660, "kg/m3"), card),
            "expansion": pub(qty(23.1, "µm/(m·K)"), card),
        },
    }


def references():
    return [
        {
            "source": f"{KIM}; Son et al. 2019, Appl Sci 9:4571",
            "quantity": "housing mass; housing modes",
            "value": "4.836 kg; 1352.7-2939.0 Hz",
            "conditions": "7 kW, ratio 12.4, two-stage, aluminium in two halves; modal test, "
            "free-free",
            "confidence": "read in the papers (mass, Table 4 modes)",
        },
        {
            "source": "Jäger and Linde 2025, World Electr Veh J 16:552, Table 2",
            "quantity": "mass; rotational deformation; first mode",
            "value": "8.41 kg; 9.34 µm; 1294-1408 Hz across materials",
            "conditions": "planetary housing, 150 kW, 2400 N·m output; fixed on one side, torque "
            "at the other; simulated",
            "confidence": "read in the paper",
        },
        {
            "source": "Marano et al. 2021, Gear Technology, Table 8",
            "quantity": "first ten modes",
            "value": "238-719 Hz",
            "conditions": "two-stage e-axle on its mountings",
            "confidence": "via fastcae research (gearbox-housing engineering, High)",
        },
        {
            "source": "Jixie chuandong 2021 (two-speed EV transmission housing)",
            "quantity": "bearing-hole displacement",
            "value": "0.085 mm before, 0.07 mm after optimisation",
            "conditions": "not read in full",
            "confidence": "abstract only",
        },
    ]


def bearing(seat, designation, kind, od, width, citation_designation=None, assumption_id=None):
    """A bearing: its designation published (cited) or assumed; its size from ISO 15."""
    named = (
        asm(designation, assumption_id) if assumption_id else pub(designation, citation_designation)
    )
    return {
        "seat": seat,
        "designation": named,
        "type": kind,
        "outer_diameter": std(qty(od, "mm"), ISO15),
        "width": std(qty(width, "mm"), ISO15),
    }


def hofstetter2018_posed():
    t2 = f"{HOF}, Table 2"
    t3 = f"{HOF}, Table 3, benchmark column"
    return {
        "schema_version": "0.1",
        "stage": "posed",
        "task": {
            "id": "hofstetter2018-l1-hpdc",
            "title": "Hofstetter et al. 2018's demonstration gearbox: an L1 housing, high-pressure "
            "die cast",
            "family": "single-speed two-stage helical reducer with integrated differential",
            "level": "L1",
            "priorities": [],
            "budget_fe_proofs": 16,
            "budget_hours": 4.0,
        },
        "requirement": {
            "style": "package",
            "torques": [
                torque("input", "nominal", "drive", pub(qty(366, "N·m"), t2)),
                torque("input", "peak", "drive", asm(qty(366, "N·m"), "A1")),
                torque("input", "peak", "regeneration", asm(qty(366, "N·m"), "A1")),
                torque("input", "peak", "reverse", asm(qty(366, "N·m"), "A1")),
            ],
            "speeds": [
                {"shaft": "input", "kind": "maximum", "speed": pub(qty(15000, "rpm"), t2)},
            ],
            "total_ratio": pub(qty(9.32, "1"), t2),
            "ratio_tolerance": pub(qty(1, "%"), t2),
            "input_output_offset": pub(
                qty(165, "mm"),
                t2,
                "'Total center distance', read as the straight-line offset between the input "
                "and output axes (the paper's requirement b); to check against its Fig. 4",
            ),
            "service_life": pub(qty(944, "h"), t2),
            "gear_material": pub("20MnCr5", t2),
            "gear_quality": asm("N6", "A2"),
            "stages": [],
            "bearings": [
                bearing("input/main", "6206", "deep_groove_ball", 62, 16, f"{t3}, Bearing 1"),
                bearing("input/cover", "NU205-E", "cylindrical_roller", 52, 15, f"{t3}, Bearing 2"),
                bearing("intermediate/main", "32010", "tapered_roller", 80, 20, f"{t3}, Bearing 3"),
                bearing(
                    "intermediate/cover", "32010", "tapered_roller", 80, 20, f"{t3}, Bearing 4"
                ),
                bearing("output/main", "6012", "deep_groove_ball", 95, 18, f"{t3}, Bearing 5"),
                bearing("output/cover", "6011", "deep_groove_ball", 90, 18, f"{t3}, Bearing 6"),
            ],
            "installation_space": {
                "kind": "layout_envelope",
                "clearance": asm(qty(20, "mm"), "A3"),
            },
        },
        "limits": limits(
            [asm(qty(7500, "rpm"), "A5"), asm(qty(15000, "rpm"), "A5")],
        ),
        "manufacturing": manufacturing(
            [
                {"part": "main", "direction": asm(vec(0, 0, 1, "1"), "A7")},
                {"part": "cover", "direction": asm(vec(0, 0, -1, "1"), "A7")},
            ]
        ),
        "references": references(),
        "assumptions": [
            assumption(
                "A1",
                "peak drive, regeneration and reverse torques",
                "366 N·m each, at the input shaft",
                "the paper gives only the nominal input torque",
            ),
            assumption("A2", "gear quality grade", "N6 (JGMA)", "no grade is published"),
            assumption(
                "A3",
                "installation space",
                "the layout's envelope grown by 20 mm",
                "the paper shows the space only as a figure (Fig. 1b)",
            ),
            assumption(
                "A4",
                "supports for the verdict",
                "motor flange clamped; one torque-reaction mount pad fixed",
                "the mount scheme is not published (the paper's unit integrates the motor)",
            ),
            assumption(
                "A5",
                "order-check speeds",
                "7500 and 15000 rpm at the input",
                "no duty spectrum is published; half and full of the maximum speed",
            ),
            assumption(
                "A6",
                "the housing's share of each tolerance",
                "half",
                "no public source gives the share (fastcae research, gearbox engineering §1.2)",
            ),
            assumption(
                "A7",
                "pull direction",
                "normal to the split face: +z for the main housing, -z for the cover",
                "a two-part housing drawn from its split",
            ),
            assumption(
                "A8",
                "which bearing of each shaft sits in the main housing",
                "Bearings 1, 3, 5 in the main housing; 2, 4, 6 in the cover",
                "Table 3 numbers the bearings by shaft, not by side",
            ),
        ],
    }


def agri_ev_gearbox_posed():
    t1 = f"{KIM}, Table 1"

    def gear_stage(name, pinion_shaft, gear_shaft, z1, z2, b1, b2, x1, x2, a):
        return {
            "name": name,
            "pinion_shaft": pinion_shaft,
            "gear_shaft": gear_shaft,
            "z_pinion": pub(z1, t1),
            "z_gear": pub(z2, t1),
            "normal_module": pub(qty(1.75, "mm"), t1),
            "pressure_angle": pub(qty(20, "deg"), t1),
            "helix_angle": pub(qty(25, "deg"), t1),
            "face_width_pinion": pub(qty(b1, "mm"), t1),
            "face_width_gear": pub(qty(b2, "mm"), t1),
            "profile_shift_pinion": pub(qty(x1, "1"), t1),
            "profile_shift_gear": pub(qty(x2, "1"), t1),
            "centre_distance": pub(qty(a, "mm"), t1),
        }

    omega = 2650 * 2 * math.pi / 60
    t_input = round(7000 / omega, 3)  # N·m, from the published power and speed (assumption A1)
    return {
        "schema_version": "0.1",
        "stage": "posed",
        "task": {
            "id": "kim2024-agricultural-utv-l1-hpdc",
            "title": "The agricultural electric UTV gearbox of Kim et al. 2024: an L1 housing, "
            "high-pressure die cast",
            "family": "two-stage parallel-axis helical reducer",
            "level": "L1",
            "priorities": [],
            "budget_fe_proofs": 16,
            "budget_hours": 4.0,
        },
        "requirement": {
            "style": "gear_train",
            "torques": [torque("input", "nominal", "drive", asm(qty(t_input, "N·m"), "A1"))],
            "speeds": [
                {"shaft": "input", "kind": "rated", "speed": pub(qty(2650, "rpm"), f"{KIM}, p. 2")},
            ],
            "powers": [
                {
                    "shaft": "input",
                    "kind": "rated",
                    "power": pub(qty(7, "kW"), f"{KIM}, p. 2"),
                    "at_speed": pub(qty(2650, "rpm"), f"{KIM}, p. 2"),
                }
            ],
            "total_ratio": pub(qty(12.37, "1"), f"{SON20}, p. 3"),
            "ratio_tolerance": asm(qty(0.1, "%"), "A2"),
            "stages": [
                gear_stage("s1", "input", "intermediate", 14, 46, 16, 16, 0.2, -0.7299, 57),
                gear_stage("s2", "intermediate", "output", 21, 79, 18, 16, 0.2, 0.0597, 97),
            ],
            "bearings": [],
            "installation_space": {
                "kind": "layout_envelope",
                "clearance": asm(qty(20, "mm"), "A3"),
            },
        },
        "limits": limits([asm(qty(2650, "rpm"), "A5")]),
        "manufacturing": manufacturing(
            [
                {"part": "lh", "direction": asm(vec(0, 0, 1, "1"), "A7")},
                {"part": "rh", "direction": asm(vec(0, 0, -1, "1"), "A7")},
            ]
        ),
        "references": references(),
        "assumptions": [
            assumption(
                "A1",
                "input torque",
                f"{t_input} N·m = 7 kW / (2650 rpm)",
                "the paper's '22 Nm' output load conflicts with its 7 kW; the torque is taken "
                "from the published power and speed",
            ),
            assumption(
                "A2",
                "ratio tolerance",
                "0.1 %",
                "the published total ratio (12.37) is rounded; the teeth give 12.36",
            ),
            assumption(
                "A3",
                "installation space",
                "the layout's envelope grown by 20 mm",
                "no package is published",
            ),
            assumption(
                "A5",
                "order-check speed",
                "2650 rpm, the rated input speed",
                "no duty spectrum is published",
            ),
            assumption(
                "A6",
                "the housing's share of each tolerance",
                "half",
                "no public source gives the share",
            ),
            assumption(
                "A7",
                "pull directions",
                "+z for the LH half, -z for the RH half",
                "the housing is two bolted halves (Kim et al. 2024); drawn from the split",
            ),
        ],
    }


def textbook_two_bearing_derived():
    beta = math.radians(25)
    mn = round(60 * math.cos(beta) / 20, 6)  # z 20 with this module gives the example's d = 60 mm
    inputs = "T=300 N·m; d=60 mm; alpha_n=20 deg; beta=25 deg; span 120 mm, gear centred"
    tool = stamp("manual-1", "1", inputs)
    t = 300e3  # N·mm
    ft = 2 * t / 60.0
    fr = ft * math.tan(math.radians(20)) / math.cos(beta)
    fa = ft * math.tan(beta)
    a_y = 0.5 * fr - 60.0 / (2 * 120.0) * fa
    b_y = 0.5 * fr + 60.0 / (2 * 120.0) * fa

    def seat(name, z):
        return {
            "name": name,
            "shaft": "pinion",
            "centre": drv(vec(0, 0, z, "mm"), tool),
            "axis": drv(vec(0, 0, 1, "1"), tool),
            "diameter": drv(qty(62, "mm"), tool),
            "width": drv(qty(16, "mm"), tool),
            "shoulder": "+axis",
            "stock": drv(qty(0.25, "mm"), tool),
        }

    return {
        "schema_version": "0.1",
        "stage": "derived",
        "task": {
            "id": "textbook-two-bearing",
            "title": "One helical gear between two bearings (a worked example)",
            "family": "a gear on a shaft between two bearings",
            "level": "L1",
            "priorities": [],
            "budget_fe_proofs": 4,
            "budget_hours": 1.0,
        },
        "requirement": {
            "style": "gear_train",
            "torques": [torque("pinion", "peak", "drive", pub(qty(300, "N·m"), GHE))],
            "total_ratio": asm(qty(2, "1"), "A1"),
            "ratio_tolerance": asm(qty(0.1, "%"), "A1"),
            "stages": [
                {
                    "name": "s1",
                    "pinion_shaft": "pinion",
                    "gear_shaft": "wheel",
                    "z_pinion": asm(20, "A1"),
                    "z_gear": asm(40, "A1"),
                    "normal_module": asm(qty(mn, "mm"), "A1"),
                    "pressure_angle": pub(qty(20, "deg"), GHE),
                    "helix_angle": pub(qty(25, "deg"), GHE),
                    "centre_distance": asm(qty(90, "mm"), "A1"),
                }
            ],
            "bearings": [
                bearing("a", "6206", "deep_groove_ball", 62, 16, assumption_id="A2"),
                bearing("b", "6206", "deep_groove_ball", 62, 16, assumption_id="A2"),
            ],
            "installation_space": {
                "kind": "box",
                "box_min": asm(vec(-100, -100, -50, "mm"), "A3"),
                "box_max": asm(vec(100, 100, 200, "mm"), "A3"),
            },
        },
        "interfaces": {"seats": [seat("a", 0.0), seat("b", 120.0)]},
        "physics": {
            "load_cases": [
                {
                    "name": "drive",
                    "seat_loads": [
                        {
                            "seat": "a",
                            "force": drv(vec(round(ft / 2, 3), round(a_y, 3), 0, "N"), tool),
                        },
                        {
                            "seat": "b",
                            "force": drv(
                                vec(round(ft / 2, 3), round(b_y, 3), round(fa, 3), "N"), tool
                            ),
                        },
                    ],
                }
            ]
        },
        "limits": limits([asm(qty(3000, "rpm"), "A4")]),
        "manufacturing": manufacturing(
            [{"part": "main", "direction": asm(vec(0, 0, 1, "1"), "A4")}]
        ),
        "references": [],
        "assumptions": [
            assumption(
                "A1",
                "the gear pair",
                "z 20/40; module chosen so the pinion's pitch diameter is the example's 60 mm",
                "the worked example states d, not the teeth",
                varied=False,
            ),
            assumption("A2", "bearings", "two 6206", "the example names none", varied=False),
            assumption("A3", "installation space", "a 200 x 200 x 250 mm box", "for the example"),
            assumption(
                "A4", "limits and process", "the defaults", "the example is about loads only"
            ),
            assumption("A6", "the housing's share", "half", "the default", varied=False),
        ],
    }


EXAMPLES = {
    "hofstetter2018_posed.json": hofstetter2018_posed,
    "agri_ev_gearbox_posed.json": agri_ev_gearbox_posed,
    "textbook_two_bearing_derived.json": textbook_two_bearing_derived,
}


def write_all() -> None:
    for name, build in EXAMPLES.items():
        text = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
        (HERE / name).write_text(text, encoding="utf-8")
        print(f"wrote {HERE / name}")


if __name__ == "__main__":
    write_all()
