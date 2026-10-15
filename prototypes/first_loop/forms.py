"""PROTOTYPE (LOP-7) - the trade's forms on the lobed shell, as named designs, built and judged.

Each design is the 6 mm-walled lobed shell plus forms from the trade-and-art note (section 5):
the wheel (spokes from every boss to a rim on each end face), gussets along the lobes from the
flange lip to the end face, and delta ribs between neighbouring bosses. The settings are the
designs' parameters; a sizing sweep changes them one at a time.

Run: uv run python prototypes/first_loop/forms.py <design> [build|judge|both] [size_mm]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import lobed  # noqa: E402

WHEEL = {"count": 8, "depth": 20.0, "thickness": 6.0, "rim_width": 6.0, "rim_depth": 12.0}
DEEP = {"count": 6, "depth": 35.0, "thickness": 5.0, "rim_width": 5.0, "rim_depth": 15.0}
GUSSETS = {"every_deg": 45.0, "depth": 12.0, "out": 18.0, "thickness": 6.0}
DELTA = {"depth": 20.0, "thickness": 6.0}
DISH = {"rise": 20.0, "faces": [("intermediate", "-z"), ("intermediate", "+z"), ("output", "-z"), ("output", "+z")]}
COLLAR = {"thickness": 14.0, "ratio": 1.4}
INNER = {"count": 8, "thickness": 6.0, "length": 25.0}
LATTICE = {"pitch": 60.0, "depth": 35.0, "thickness": 5.0, "rim_width": 0.0, "rim_depth": 0.0}
INNER_LATTICE = {"pitch": 60.0, "depth": 20.0, "thickness": 5.0}

DESIGNS = {
    # the night's best, rebuilt with the construction planes snapped (comparability)
    "lobed_e10s": {"end_wall": 10.0},
    # (1) the wheel on every end face but the motor's
    "wheel1": {"end_wall": 6.0, "wheel": WHEEL},
    # (2) the wheel with gussets along the lobes
    "wheel2": {"end_wall": 6.0, "wheel": WHEEL, "gussets": GUSSETS},
    # (3) the wheel with the delta ribs between bosses
    "wheel3": {"end_wall": 6.0, "wheel": WHEEL, "delta": DELTA},
    # (1 + 2 + 3) everything, to see the ceiling at this mass
    "wheel4": {"end_wall": 6.0, "wheel": WHEEL, "gussets": GUSSETS, "delta": DELTA},
    # the wheel on 8 mm end walls
    "wheel1_e8": {"end_wall": 8.0, "wheel": WHEEL},
    # the sizing rule of the trade: thinner and deeper spokes, fewer of them (Son 2019's 4 mm
    # gussets, GRM's 5 mm ribs); a rib's stiffness grows with the cube of its depth
    "wheel5": {"end_wall": 6.0, "wheel": DEEP},
    "wheel6": {"end_wall": 8.0, "wheel": DEEP},
    "wheel7": {"end_wall": 6.0, "wheel": DEEP, "gussets": {**GUSSETS, "thickness": 5.0, "depth": 15.0, "out": 25.0}, "delta": {**DELTA, "thickness": 5.0, "depth": 30.0}},
    # (3) the dish: the thrust-bearing end walls as shallow cones, alone and under the deep wheel
    "dish0": {"end_wall": 6.0, "dish": DISH},
    "dish1": {"end_wall": 6.0, "dish": DISH, "wheel": DEEP},
    # (6) the collar: the end wall 16 mm thick round each boss, 6 mm elsewhere; alone, and
    # under the deep wheel
    "collar1": {"end_wall": 6.0, "collar": COLLAR},
    "collar2": {"end_wall": 6.0, "collar": COLLAR, "wheel": DEEP},
    # thickness where the seats bind: the intermediate's and output's end walls thick, the
    # input's less, no ribs; then with collars
    "walls1": {"end_wall": 8.0, "end_walls": {"intermediate": 12.0, "output": 12.0}},
    "walls2": {"end_wall": 8.0, "end_walls": {"intermediate": 12.0, "output": 12.0}, "collar": {"thickness": 18.0, "ratio": 1.4}},
    # Son 2019's gussets at every boss's root, inside the housing: on the 10 mm walls, and on
    # 8 mm walls with collars
    "ing1": {"end_wall": 10.0, "inner_gussets": INNER},
    "ing2": {"end_wall": 8.0, "inner_gussets": INNER, "collar": COLLAR},
    # GRM's cross-hatched lattice on every end face, 5 mm ribs: 60 mm pitch 35 deep on 6 mm
    # walls; the same at 45 degrees; a denser and shallower one
    "lat1": {"end_wall": 6.0, "lattice": LATTICE},
    "lat2": {"end_wall": 6.0, "lattice": {**LATTICE, "angle": 45.0}},
    "lat3": {"end_wall": 6.0, "lattice": {**LATTICE, "pitch": 45.0, "depth": 25.0}},
    "lat4": {"end_wall": 6.0, "lattice": {**LATTICE, "rim_width": 5.0, "rim_depth": 12.0}},
    # the lattice inside too: on the motor side only (where the motor leaves no room outside),
    # and on both
    "lat5": {"end_wall": 6.0, "lattice": LATTICE, "inner_lattice": {**INNER_LATTICE, "sides": ("-z",)}},
    "lat6": {"end_wall": 6.0, "lattice": LATTICE, "inner_lattice": INNER_LATTICE},
    # The box: the lattice closed by a skin, outside on the cover and wherever the motor allows,
    # inside on the motor side - each end wall a cored double wall (printed sand mould)
    "box1": {"end_wall": 6.0, "lattice": {**LATTICE, "skin": 4.0},
             "inner_lattice": {**INNER_LATTICE, "sides": ("-z",), "skin": 4.0}},
    # the box with 12 mm bosses and the gussets inside at the bosses' roots
    "box2": {"end_wall": 6.0, "boss": 12.0, "lattice": {**LATTICE, "skin": 4.0},
             "inner_lattice": {**INNER_LATTICE, "sides": ("-z",), "skin": 4.0}, "inner_gussets": INNER},
    # Robust forms only (what the mesher handles): the motor side's end walls thick, growing
    # inward where the motor leaves no room outside; the cover's end walls with the outside
    # lattice; 12 mm bosses; the gussets inside at the bosses' roots
    "hyb1": {"end_wall": 6.0, "boss": 12.0, "inner_gussets": INNER,
             "end_walls": {"intermediate": {"-z": 20.0, "+z": 6.0}, "output": {"-z": 14.0, "+z": 6.0}, "input": {"-z": 6.0, "+z": 8.0}},
             "lattice": {**LATTICE, "sides": ("+z",)}},
    # the same with the motor side's walls thicker still, and 8 mm cover walls under the lattice
    "hyb2": {"end_wall": 6.0, "boss": 12.0, "inner_gussets": INNER,
             "end_walls": {"intermediate": {"-z": 26.0, "+z": 8.0}, "output": {"-z": 18.0, "+z": 8.0}, "input": {"-z": 8.0, "+z": 10.0}},
             "lattice": {**LATTICE, "sides": ("+z",)}},
    # hyb1 without the gussets inside (they are the meshes' other risk)
    "hyb3": {"end_wall": 6.0, "boss": 12.0,
             "end_walls": {"intermediate": {"-z": 20.0, "+z": 6.0}, "output": {"-z": 14.0, "+z": 6.0}, "input": {"-z": 6.0, "+z": 8.0}},
             "lattice": {**LATTICE, "sides": ("+z",)}},
    # Aimed at a pass, whatever it weighs: everything the ceilings ask for, in robust forms
    "pass1": {"wall": 8.0, "end_wall": 8.0, "boss": 14.0, "inner_gussets": INNER,
              "end_walls": {"intermediate": {"-z": 30.0, "+z": 8.0}, "output": {"-z": 24.0, "+z": 8.0}, "input": {"-z": 10.0, "+z": 10.0}},
              "lattice": {**LATTICE, "depth": 40.0, "pitch": 50.0, "sides": ("+z",)}},
    # pass1 showed only the intermediate's seats failing: the stiffness goes to the intermediate's
    # lobe (end walls and side walls), the input's and output's lobes lighter
    "int1": {"wall": 6.0, "end_wall": 8.0, "boss": 12.0, "inner_gussets": INNER, "walls": {"intermediate": 12.0},
             "end_walls": {"intermediate": {"-z": 30.0, "+z": 20.0}, "output": {"-z": 18.0, "+z": 8.0}, "input": {"-z": 10.0, "+z": 10.0}},
             "lattice": {**LATTICE, "depth": 40.0, "pitch": 50.0, "sides": ("+z",)}},
    "int2": {"wall": 6.0, "end_wall": 8.0, "boss": 12.0, "inner_gussets": INNER, "walls": {"intermediate": 16.0},
             "end_walls": {"intermediate": {"-z": 34.0, "+z": 26.0}, "output": {"-z": 14.0, "+z": 8.0}, "input": {"-z": 8.0, "+z": 8.0}},
             "lattice": {**LATTICE, "depth": 40.0, "pitch": 50.0, "sides": ("+z",)}},
    # the box with the intermediate's lobe stiffened: its side walls 12 mm, its end walls 12 under
    # the boxes; hoops round every lobe
    "boxint1": {"end_wall": 6.0, "walls": {"intermediate": 12.0},
                "end_walls": {"intermediate": {"-z": 12.0, "+z": 12.0}},
                "lattice": {**LATTICE, "skin": 4.0},
                "inner_lattice": {**INNER_LATTICE, "sides": ("-z",), "skin": 4.0}},
    "boxint2": {"end_wall": 6.0, "walls": {"intermediate": 12.0},
                "end_walls": {"intermediate": {"-z": 12.0, "+z": 12.0}},
                "lattice": {**LATTICE, "skin": 4.0},
                "inner_lattice": {**INNER_LATTICE, "sides": ("-z",), "skin": 4.0},
                "hoops": {"count": 2, "height": 12.0, "thickness": 6.0}},
    # box1 against the chord tilt: a stiffer flange; 8 mm side walls; the third mount on the
    # cover (a what-if of A20, the mounts the example does not give)
    "box1_fl": {"end_wall": 6.0, "flange_thickness": 12.0, "lattice": {**LATTICE, "skin": 4.0},
                "inner_lattice": {**INNER_LATTICE, "sides": ("-z",), "skin": 4.0}},
    "box1_sw": {"end_wall": 6.0, "wall": 8.0, "lattice": {**LATTICE, "skin": 4.0},
                "inner_lattice": {**INNER_LATTICE, "sides": ("-z",), "skin": 4.0}},
    "box1_cm": {"end_wall": 6.0, "mount_sides": ["-z", "-z", "+z"], "lattice": {**LATTICE, "skin": 4.0},
                "inner_lattice": {**INNER_LATTICE, "sides": ("-z",), "skin": 4.0}},
    # box2 with hoops round the lobes against their ovalising
    "box3": {"end_wall": 6.0, "boss": 12.0, "lattice": {**LATTICE, "skin": 4.0},
             "inner_lattice": {**INNER_LATTICE, "sides": ("-z",), "skin": 4.0}, "inner_gussets": INNER,
             "hoops": {"count": 2, "height": 12.0, "thickness": 6.0}},
}


def main(design: str, what: str = "both", size: float = 8.0) -> None:
    if what in ("build", "both"):
        result = lobed.build(design, overrides=DESIGNS[design])
        print(f"{design}: {result['mass_kg']['total']:.3f} kg")
    if what in ("judge", "both"):
        subprocess.run(
            [sys.executable, str(HERE / "fe.py"), design, str(size)], check=True, cwd=str(ROOT)
        )


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1] if len(a) > 1 else "both", float(a[2]) if len(a) > 2 else 8.0)
