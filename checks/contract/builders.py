"""Small builders for contract tests: plain dicts, so a test can break one value at a time."""

import copy

CITE = "Hofstetter et al. 2018, Forsch Ingenieurwes 82:361-370, Table 2"
STAMP = {
    "kind": "derived",
    "tool": "manual",
    "tool_version": "1",
    "input_hash": "sha256:" + "0" * 64,
}


def qty(value, unit):
    return {"value": value, "unit": unit}


def vec(x, y, z, unit):
    return {"values": [x, y, z], "unit": unit}


def published(value, citation=CITE, authority="engineer_locked", kind="hard"):
    return {
        "value": value,
        "provenance": {"kind": "published", "citation": citation},
        "authority": authority,
        "kind": kind,
    }


def standard(value, citation, kind="hard"):
    return {
        "value": value,
        "provenance": {"kind": "standard", "citation": citation},
        "authority": "engineer_locked",
        "kind": kind,
    }


def assumed(value, assumption_id, kind="hard"):
    return {
        "value": value,
        "provenance": {"kind": "assumption", "assumption_id": assumption_id},
        "authority": "engineer_locked",
        "kind": kind,
    }


def derived(value, stamp=None):
    return {
        "value": value,
        "provenance": dict(stamp or STAMP),
        "authority": "engineer_locked",
        "kind": "derived",
    }


def limits():
    return {
        "verdict_rule_version": "v0.1",
        "mesh_misalignment_share": assumed(qty(50, "%"), "A6"),
        "centre_distance_share": assumed(qty(50, "%"), "A6"),
        "ovalisation_share": assumed(qty(50, "%"), "A6"),
        "bearing_tilt": [
            {
                "bearing_type": kind,
                "limit": standard(qty(limit, "mrad"), "Shigley, Table 7-2"),
            }
            for kind, limit in (
                ("tapered_roller", 0.5),
                ("cylindrical_roller", 0.8),
                ("deep_groove_ball", 1.0),
            )
        ],
        "order_separation": standard(qty(3, "%"), "Marano et al. 2021"),
        "order_check_at": assumed("maximum", "A5"),
        "model_margin": standard(qty(25, "%"), "Gutierrez Santiago et al. 2023"),
        "objective": "least_mass",
        "stress": "recorded",
    }


def manufacturing():
    nadca = "NADCA 2015, Section 4A"
    card = "Kim et al. 2024, Sci Rep 14:4145, Table 3"
    return {
        "process": "high_pressure_die_casting",
        "pull_directions": [{"part": "main", "direction": assumed(vec(0, 0, 1, "1"), "A7")}],
        "draft_inside": standard(qty(2, "deg"), nadca),
        "draft_outside": standard(qty(1, "deg"), nadca),
        "draft_min_depth": standard(qty(25.4, "mm"), nadca),
        "min_wall": standard(qty(4, "mm"), "plan D7 (least member)"),
        "machining_stock": standard(qty(0.25, "mm"), nadca),
        "material": {
            "name": "aluminium housing card",
            "youngs_modulus": published(qty(70.93, "GPa"), card),
            "poisson_ratio": published(qty(0.3135, "1"), card),
            "density": published(qty(2660, "kg/m3"), card),
        },
    }


def assumptions():
    return [
        {"id": "A3", "what": "installation space", "value": "+20 mm", "why": "x", "varied": True},
        {
            "id": "A5",
            "what": "order-check speeds",
            "value": "15000 rpm",
            "why": "x",
            "varied": True,
        },
        {"id": "A6", "what": "housing share", "value": "half", "why": "x", "varied": True},
        {"id": "A7", "what": "pull direction", "value": "+z", "why": "x", "varied": True},
    ]


def minimal_posed():
    """A posed, package-style contract with only what the schema requires."""
    return {
        "schema_version": "0.1",
        "stage": "posed",
        "task": {
            "id": "test-minimal",
            "title": "A minimal posed contract",
            "family": "two-stage parallel-axis helical reducer",
            "level": "L1",
            "budget_fe_proofs": 16,
            "budget_hours": 4.0,
        },
        "requirement": {
            "style": "package",
            "torques": [
                {
                    "shaft": "input",
                    "kind": "nominal",
                    "direction": "drive",
                    "torque": published(qty(366, "N·m")),
                }
            ],
            "speeds": [
                {"shaft": "input", "kind": "maximum", "speed": assumed(qty(15000, "rpm"), "A5")}
            ],
            "total_ratio": published(qty(9.32, "1")),
            "ratio_tolerance": published(qty(1, "%")),
            "input_output_offset": published(qty(165, "mm")),
            "installation_space": {
                "kind": "layout_envelope",
                "clearance": assumed(qty(20, "mm"), "A3"),
            },
        },
        "limits": limits(),
        "manufacturing": manufacturing(),
        "assumptions": assumptions(),
    }


def stage(name, pinion_shaft, gear_shaft, z1, z2, mn, x1, x2, beta=25.0, alpha=20.0):
    """A stage with its full gear data, which fix its centre distance: so it carries none."""
    test = "test data"
    return {
        "name": name,
        "pinion_shaft": pinion_shaft,
        "gear_shaft": gear_shaft,
        "z_pinion": published(z1, test),
        "z_gear": published(z2, test),
        "normal_module": published(qty(mn, "mm"), test),
        "pressure_angle": published(qty(alpha, "deg"), test),
        "helix_angle": published(qty(beta, "deg"), test),
        "profile_shift_pinion": published(qty(x1, "1"), test),
        "profile_shift_gear": published(qty(x2, "1"), test),
    }


def gear_train_posed():
    """A posed gear_train-style contract: two shifted helical stages, power and torque."""
    data = minimal_posed()
    data["task"]["id"] = "test-gear-train"
    req = data["requirement"]
    req["style"] = "gear_train"
    req["stages"] = [
        stage("s1", "input", "intermediate", 14, 46, 1.75, 0.2, -0.7299),
        stage("s2", "intermediate", "output", 21, 79, 1.75, 0.2, 0.0597),
    ]
    # The teeth fix the ratio: it is no input here.
    del req["total_ratio"], req["ratio_tolerance"]
    req["input_output_offset"] = published(qty(120, "mm"), "test data")
    req["torques"] = [
        {
            "shaft": "input",
            "kind": "nominal",
            "direction": "drive",
            "torque": published(qty(25.22, "N·m"), "test data"),
        }
    ]
    req["speeds"] = [
        {"shaft": "input", "kind": "rated", "speed": published(qty(2650, "rpm"), "test data")}
    ]
    data["limits"]["order_check_at"] = published("rated", "test data")
    req["powers"] = [
        {
            "shaft": "input",
            "kind": "rated",
            "power": published(qty(7, "kW"), "test data"),
            "at_speed": published(qty(2650, "rpm"), "test data"),
        }
    ]
    return data


def seat(name, shaft, z):
    return {
        "name": name,
        "shaft": shaft,
        "centre": derived(vec(0, 0, z, "mm")),
        "axis": derived(vec(0, 0, 1, "1")),
        "diameter": derived(qty(62, "mm")),
        "width": derived(qty(16, "mm")),
        "shoulder": "+axis",
        "stock": derived(qty(0.25, "mm")),
    }


def two_bearing_derived():
    """A derived contract: one gear between two bearings (GHE §6.2's worked example)."""
    data = minimal_posed()
    data["task"]["id"] = "test-two-bearing"
    data["stage"] = "completed"
    req = data["requirement"]
    req["style"] = "gear_train"
    mn = 60.0 * 0.9063077870366499 / 20  # so that the pinion's pitch diameter is 60 mm
    req["stages"] = [stage("s1", "pinion", "wheel", 20, 40, mn, 0.0, 0.0)]
    del req["total_ratio"], req["ratio_tolerance"]
    req["torques"] = [
        {
            "shaft": "pinion",
            "kind": "peak",
            "direction": "drive",
            "torque": published(qty(300, "N·m"), "test data"),
        }
    ]
    req["bearings"] = [
        {
            "seat": "a",
            "designation": published("6206", "test data"),
            "type": "deep_groove_ball",
            "outer_diameter": published(qty(62, "mm"), "test data"),
        },
        {
            "seat": "b",
            "designation": published("6206", "test data"),
            "type": "deep_groove_ball",
            "outer_diameter": published(qty(62, "mm"), "test data"),
        },
    ]
    req["installation_space"] = {
        "kind": "box",
        "box_min": published(vec(-100, -100, -50, "mm"), "test data"),
        "box_max": published(vec(100, 100, 200, "mm"), "test data"),
    }
    data["interfaces"] = {"seats": [seat("a", "pinion", 0.0), seat("b", "pinion", 120.0)]}
    data["physics"] = {
        "load_cases": [
            {
                "name": "drive",
                "seat_loads": [
                    {"seat": "a", "force": derived(vec(5000.0, 842.2, 0.0, "N"))},
                    {"seat": "b", "force": derived(vec(5000.0, 3173.8, 4663.1, "N"))},
                ],
            }
        ]
    }
    return data


def clone(d):
    return copy.deepcopy(d)
