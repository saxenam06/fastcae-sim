"""PROTOTYPE - not product code, not the judge.

Shared reader for plan Part C, Tasks 9-11: turns derived.json (Task 8) into the plain geometric
quantities that core.py, field.py, join.py and render.py all use, so the four agree on every
position. Nothing here adds a number of its own except the shoulder-hole size (prototype choice,
labelled below) and the prototype parameters imported from params.py.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

import numpy as np
import params as P


@dataclass
class Gear:
    name: str
    shaft: str
    cx: float
    cy: float
    r_pitch: float
    r_tip: float
    z0: float
    z1: float

    @property
    def r_keepout(self):
        return self.r_tip + P.GEAR_RADIAL_CLEARANCE

    @property
    def z_keepout(self):
        return self.z0 - P.GEAR_AXIAL_CLEARANCE, self.z1 + P.GEAR_AXIAL_CLEARANCE


@dataclass
class Seat:
    name: str
    shaft: str
    side: str  # "back" or "cover"
    bearing: str
    cx: float
    cy: float
    d: float  # bearing bore
    D: float  # bearing outside diameter = seat diameter
    B: float  # bearing width
    z0: float
    z1: float
    through: bool  # shoulder has a shaft passage

    @property
    def ring_top(self):
        return self.z1 + P.SHOULDER

    @property
    def r_ring_top(self):
        """Outer radius of the seat ring at its top: bore radius + 8 mm (the brief)."""
        return self.D / 2 + P.RING_WALL

    def r_ring(self, z):
        """Outer radius of the ring at height z: 8 mm wall at the top, growing downward with
        the draft (the ring's outside is a cast face drawn along +z)."""
        return self.r_ring_top + (self.ring_top - np.asarray(z)) * P.tan_draft()

    @property
    def r_shoulder_hole(self):
        """Shaft passage through the shoulder: radius (d + D) / 4, i.e. the bearing's mean
        diameter, so the outer ring keeps its abutment (prototype choice)."""
        return (self.d + self.D) / 4 if self.through else None


class Layout:
    def __init__(self, derived: dict):
        self.derived = derived
        h = derived["housing"]
        self.z_keepout_top = h["gear_keepout_top_z"]["value"]
        self.z_wall_in = h["back_wall_inner_z"]["value"]
        self.z_wall_out = h["back_wall_outer_z"]["value"]
        self.L = h["L"]["value"]
        self.tan = P.tan_draft()

        self.gears = []
        for g in derived["gears"]:
            c = g["centre"]["value"]
            z0, z1 = g["axial_station"]["value"]
            self.gears.append(
                Gear(
                    g["name"],
                    g["shaft"],
                    c[0],
                    c[1],
                    g["pitch_diameter"]["value"] / 2,
                    g["tip_diameter"]["value"] / 2,
                    z0,
                    z1,
                )
            )
        self.axes = {k: tuple(v["value"][:2]) for k, v in derived["axes"].items()}

        self.seats = []
        for s in derived["seats"]:
            c = s["centre"]["value"]
            z0, z1 = s["z_range"]["value"]
            hole = s["shoulder_hole"]["value"]
            self.seats.append(
                Seat(
                    s["name"],
                    s["shaft"],
                    "back" if s["side"].startswith("back") else "cover",
                    s["bearing"]["value"],
                    c[0],
                    c[1],
                    s["bore_d"]["value"],
                    s["diameter"]["value"],
                    s["width"]["value"],
                    z0,
                    z1,
                    bool(hole and hole.startswith("through")),
                )
            )
        self.back = [s for s in self.seats if s.side == "back"]
        self.back_by = {s.shaft: s for s in self.back}
        self.cover_by = {s.shaft: s for s in self.seats if s.side == "cover"}

        mf = derived["interfaces"]["motor_flange"]
        self.flange_c = tuple(mf["centre"]["value"][:2])
        self.z_flange = mf["centre"]["value"][2]
        self.z_flange_bottom = mf["z_bottom"]["value"]
        self.flange_r_out = mf["outside_diameter"]["value"] / 2
        self.flange_r_spigot = mf["spigot_diameter"]["value"] / 2
        self.flange_spigot_depth = mf["spigot_depth"]["value"]
        self.flange_r_bolt = mf["bolt_circle_diameter"]["value"] / 2
        self.flange_bolts = mf["bolt_count"]["value"]
        self.flange_hole_r = mf["bolt_hole_diameter"]["value"] / 2

        mp = derived["interfaces"]["mount_pad"]
        self.pad_face_x = mp["face_x"]["value"]
        hz, wy, tx = mp["size_z_y_x"]["value"]
        cz = mp["centre"]["value"][2]
        self.pad_z = (cz - hz / 2, cz + hz / 2)
        self.pad_half_y = wy / 2
        self.pad_thickness = tx
        self.pad_hole_r = mp["hole_diameter"]["value"] / 2
        self.pad_hole_z = mp["hole_z"]["value"]

        sp = derived["installation_space"]
        self.space_lo = np.array(sp["lo"]["value"])
        self.space_hi = np.array(sp["hi"]["value"])

    # ---- draft: the shell's offset from the keep-outs grows toward the split face, so the
    # cavity is widest at the opening (z = 0) and every side wall leans inward along +z.
    def delta(self, z):
        return np.maximum(self.z_wall_in - np.asarray(z, dtype=np.float64), 0.0) * self.tan

    def pad_half_y_at(self, z):
        """The pad's +-y faces lean inward along +z with the draft (half-width at z)."""
        return self.pad_half_y - (np.asarray(z) - self.pad_z[0]) * self.tan

    def boss_level_f(self):
        """Field level f of the bolt-boss centres: the wall's outer surface + 5 mm."""
        return P.SHELL_GAP + P.SHELL_WALL + P.BOSS_BEYOND_WALL

    def output_cavity_radius(self, z):
        """Inner surface of the shell around the output wheel (the +x end), at height z."""
        g4 = next(g for g in self.gears if g.name == "g4")
        return g4.r_keepout + P.SHELL_GAP + self.delta(z)


def smin(a, b, k):
    """Polynomial smooth minimum (blend radius about k)."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1.0 - h) + a * h - k * h * (1.0 - h)


def outline_d2(layout: Layout, x, y):
    """2D signed distance (smooth union, CAVITY_BLEND) to the gears' keep-out discs."""
    d = None
    for g in layout.gears:
        di = np.sqrt((x - g.cx) ** 2 + (y - g.cy) ** 2) - g.r_keepout
        d = di if d is None else smin(d, di, P.CAVITY_BLEND)
    return d


def load_layout():
    d = json.loads((P.OUT / "derived.json").read_text(encoding="utf-8"))
    return Layout(d)


def angle_deg(v):
    return math.degrees(math.atan2(v[1], v[0])) % 360.0


# ------------------------------------------------------------------ utilities (no psutil here)


def free_memory_mb():
    """Free physical memory in MB (Windows, via PowerShell); None if unavailable."""
    import subprocess

    try:
        out = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout.strip()
        return int(out) / 1024.0
    except Exception:
        return None


def peak_memory_mb():
    """This process's peak working set in MB (Windows psapi); None if unavailable."""
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        if not psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return None
        return pmc.PeakWorkingSetSize / 2**20
    except Exception:
        return None
