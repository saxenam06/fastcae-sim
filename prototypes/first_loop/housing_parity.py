"""PROTOTYPE (LOP-33) - the parity check of the housing's stages moved into `src/zenryx/domains/gearbox/housing`: each moved stage
run on the reference design's files (`ref/lop33/`, the engineer's: `baseline2_lw8`'s run, `baseline2_lw8_smooth`'s drawing and
judgement) and compared with what the prototype makes of the same inputs on the same machine, and with the reference files.

    housing_parity.py draw [--prototype]     the drawing: the moved `draw` against the prototype's `outcome_cad.py` (both run here)
    housing_parity.py judge                  the oil-tight gate and castability of the moved drawing, against the prototype's

The files go to data/parity/ (git-ignored). The drawing must match the prototype's exactly (the same vertices and faces); against the
reference, made on the engineer's Windows laptop, within the libraries' noise (a few vertices by a fraction of a mm)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from zenryx.domains.gearbox.housing.draw import DrawSettings  # noqa: E402

REF = ROOT / "ref" / "lop33"
OUT = ROOT / "data" / "parity"
CONTRACT = ROOT / "checks" / "data" / "contracts" / "ev_reducer_posed.json"
RUN = "topofree_mass_tilt_7.73kg_4mm_projected_band24_cup_bolts_split_contract_drive_baseline2_lw8_empty_shell_notowers_protect_modes12_fm500_hf4_single_p40_max16_flange_beds_lm8_lw8_sf1.5"  # fmt: skip
RECIPE_ENV = {"LOOP_MEMBER_P": "40", "LOOP_EXACT_WALLS": "1", "LOOP_LEAST_MEMBER": "8", "LOOP_VOXEL_SMOOTH": "3", "LOOP_DRAW_SMOOTH": "6",
              "LOOP_DRAW_SMOOTH_RANGE": "15", "LOOP_DRAW_FINE": "1"}  # fmt: skip


def setup() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("contract.json", f"{RUN}.json", f"{RUN}.npz"):
        if not (OUT / name).exists():
            shutil.copy(REF / name, OUT / name)


def meshes_equal(a: str, b: str, folder_a: Path, folder_b: Path) -> list[str]:
    """Where two drawings' halves differ: '' each for the same vertices and faces exactly, else how."""
    import trimesh
    from scipy.spatial import cKDTree

    out = []
    for half in ("motor_side", "cover"):
        ma = trimesh.load(str(folder_a / f"{a}_{half}.ply"), process=False)
        mb = trimesh.load(str(folder_b / f"{b}_{half}.ply"), process=False)
        if np.array_equal(ma.vertices, mb.vertices) and np.array_equal(ma.faces, mb.faces):
            out.append(f"{half}: identical ({len(ma.faces):,} faces)")
            continue
        d = cKDTree(mb.vertices).query(ma.vertices)[0]
        out.append(f"{half}: DIFFERENT: {len(ma.vertices):,} against {len(mb.vertices):,} vertices, {int((d > 1e-6).sum())} moved, "
                   f"at most {d.max():.3g} mm; volume {ma.volume / 1e3:.3f} against {mb.volume / 1e3:.3f} cm3")  # fmt: skip
    return out


def draw(prototype: bool) -> None:
    from zenryx.domains.gearbox.housing.draw import draw as draw_src

    setup()
    draw_src(RUN, "src_draw", OUT, CONTRACT, DrawSettings.from_env(RECIPE_ENV))
    if prototype or not (ROOT / "data" / "first_loop" / "trace_smooth_cover.ply").exists():
        # the prototype on the same inputs, in its own folder (its OUT is data/first_loop)
        env = {**os.environ, **RECIPE_ENV, "PYTHONPATH": str(ROOT / "src"), "MPLBACKEND": "Agg"}
        for name in ("contract.json", f"{RUN}.json", f"{RUN}.npz"):
            shutil.copy(REF / name, ROOT / "data" / "first_loop" / name)
        subprocess.run([sys.executable, str(HERE / "outcome_cad.py"), RUN, "trace_smooth", "skin", "mesh"], cwd=ROOT, env=env, check=True)
    print("\n".join(meshes_equal("src_draw", "trace_smooth", OUT, ROOT / "data" / "first_loop")))
    print("against the reference (the engineer's laptop):")
    print("\n".join(meshes_equal("src_draw", "baseline2_lw8_smooth", OUT, REF)))
    a = json.loads((OUT / "src_draw.json").read_text())
    b = json.loads((ROOT / "data" / "first_loop" / "trace_smooth.json").read_text())
    print("mass", a["mass_kg"], "against", b["mass_kg"])
    print("fidelity", a["skin"]["fidelity"], "against", b["skin"]["fidelity"])
    print("mounts", len(a["mounts"]), "bolts", len(a["bolts"]), "against", len(b["mounts"]), len(b["bolts"]))


def judge() -> None:
    from zenryx.domains.gearbox.housing.castable import castability
    from zenryx.domains.gearbox.housing.oiltight import check

    o = check("src_draw", OUT, CONTRACT)
    ref_o = json.loads((ROOT / "data" / "first_loop" / "oiltight_trace_smooth.json").read_text())
    same = {k: (o[k], ref_o[k]) for k in ("tight", "inside_cells", "metal_cm3") if o[k] != ref_o[k]}
    print("oil-tight:", "identical" if not same else f"DIFFERENT {same}")
    c = castability("src_draw", OUT, CONTRACT)
    ref_c = json.loads((ROOT / "data" / "first_loop" / "castable_trace_smooth.json").read_text())
    print("castability:", "identical" if c["halves"] == ref_c["halves"] else "DIFFERENT")
    if c["halves"] != ref_c["halves"]:
        for x, y in zip(c["halves"], ref_c["halves"], strict=True):
            print({k: (x[k], y[k]) for k in x if x[k] != y[k] and k != "undercut_faces"})


def _numbers(r: dict, prefix: str = "") -> dict:
    """A judgement's numbers, flat, by path."""
    out = {}
    for k, v in r.items():
        if isinstance(v, dict):
            out.update(_numbers(v, f"{prefix}{k}."))
        elif isinstance(v, (int, float)) and not isinstance(v, bool) and k not in ("seconds", "factor_s"):
            out[prefix + k] = float(v)
        elif isinstance(v, list) and v and all(isinstance(x, (int, float)) for x in v):
            out.update({f"{prefix}{k}[{i}]": float(x) for i, x in enumerate(v)})
    return out


def fe(surface: float, size: float) -> None:
    """The moved FE against the prototype's on the same drawing, here on a coarse surface (a CPU sandbox's memory); on
    the engineer's laptop with the card, `fe 7 8` judges as the recipe does, and both are compared with the reference."""
    from zenryx.domains.gearbox.housing.fe import judge as judge_src

    src = judge_src("src_draw", OUT, CONTRACT, size=size, surface=surface)
    stem = "trace_smooth" + ("" if surface == 7.0 else f"_surf{surface:g}")
    proto = ROOT / "data" / "first_loop" / f"fe_{stem}.json"
    if not proto.exists() or "--prototype" in sys.argv:
        env = {**os.environ, "LOOP_SURFACE_EDGE": f"{surface:g}", "PYTHONPATH": os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")])}
        subprocess.run([sys.executable, str(HERE / "fe.py"), "trace_smooth", f"{size:g}"], cwd=ROOT, env=env, check=True)
    worst = _compare(_numbers(src), _numbers(json.loads(proto.read_text())))
    print(f"FE against the prototype's: the largest relative difference {worst[0]:.2e} at {worst[1]}")
    if surface == 7.0 and size == 8.0:
        ref = _numbers(json.loads((REF / "fe_baseline2_lw8_smooth.json").read_text()))
        worst = _compare(_numbers(src), ref)
        print(f"FE against the reference: the largest relative difference {worst[0]:.2e} at {worst[1]}")


class StubFactor:
    """A stand-in for the single factor, the same in both judgements (`fe_glue`): x = f / diag(K). The factor itself is
    moved unchanged; what this checks is everything round it."""

    kind, factor_s = "stub", 0.0

    def __init__(self, k):
        self.k, self.d = k, k.diagonal()

    def backsolve(self, r):
        return np.asarray(r, float).reshape(-1) / self.d

    def solve(self, f, tol=0.0, most=0):
        return self.backsolve(f), 0, 0.0

    def close(self):
        pass


def stub_modes(k_red, m_red, factor, count=12, vectors=True):
    """The stand-in's modes: the stiffness's and mass's first diagonal entries, and unit vectors."""
    hz = sorted(float(np.sqrt(k_red.diagonal()[i] / m_red.diagonal()[i])) for i in range(count))
    vecs = np.zeros((k_red.shape[0], count))
    vecs[np.arange(count), np.arange(count)] = 1.0
    return (hz, vecs) if vectors else hz


def fe_glue_side(side: str, surface: float, size: float) -> None:
    """One side of `fe_glue`, in its own process (the stiffness of a full mesh takes several GB)."""
    if side == "src":
        from zenryx.domains.gearbox.housing import fe as fe_src

        fe_src.SingleFactor, fe_src.modes = StubFactor, stub_modes
        fe_src.judge("src_draw", OUT, CONTRACT, size=size, surface=surface)
    else:
        os.environ["LOOP_SURFACE_EDGE"] = f"{surface:g}"
        sys.path.insert(0, str(HERE))
        import fe as fe_proto

        fe_proto.SingleFactor, fe_proto.modes = StubFactor, stub_modes
        fe_proto.judge("trace_smooth", size)


def fe_glue(surface: float, size: float) -> None:
    """The moved FE's glue against the prototype's on the same drawing, both with `StubFactor`: the meshes, the seats,
    the loads, the couplings, the stiffness, the results and the files must be the same."""
    for side in ("prototype", "src"):
        subprocess.run([sys.executable, __file__, "fe-glue-side", side, f"{surface:g}", f"{size:g}"], cwd=ROOT, check=True)
    proto_stem = "trace_smooth" + ("" if surface == 7.0 else f"_surf{surface:g}")
    a = json.loads((OUT / "fe_src_draw.json").read_text())
    b = json.loads((ROOT / "data" / "first_loop" / f"fe_{proto_stem}.json").read_text())
    worst = _compare(_numbers(a), _numbers(b))
    print(f"FE glue against the prototype's: the largest relative difference {worst[0]:.2e} at {worst[1]}")
    za, zb = np.load(OUT / "fe_src_draw.npz"), np.load(ROOT / "data" / "first_loop" / f"fe_{proto_stem}.npz")
    for k in sorted(set(za.files) | set(zb.files)):
        same = k in za.files and k in zb.files and np.array_equal(za[k], zb[k])
        close = same or (k in za.files and k in zb.files and za[k].shape == zb[k].shape and np.allclose(za[k], zb[k], rtol=1e-12, atol=0))
        print(f"  fe npz {k}: {'identical' if same else 'within 1e-12' if close else 'DIFFERENT'}")
    ma, mb = np.load(OUT / "fe_src_draw_modes.npz"), np.load(ROOT / "data" / "first_loop" / f"fe_{proto_stem}_modes.npz")
    for k in sorted(set(ma.files) | set(mb.files)):
        same = k in ma.files and k in mb.files and np.array_equal(ma[k], mb[k])
        print(f"  modes npz {k}: {'identical' if same else 'DIFFERENT'}")


TRACE = ROOT / "data" / "ot" / "data" / "first_loop"  # the prototype's run on the CPU stand-in (the trace's own tree)
RECIPE_ARGS = ["--max-member", "16", "--band", "24", "--height-field", "4", "--empty", "--protect", "--shell-fixed", "--no-towers",
               "--objective", "mass_tilt", "--safety", "1.5", "--modes", "0.12", "--first-mode", "500", "--least-width", "8"]  # fmt: skip


def optimise(voxel: float, iterations: int) -> None:
    """The moved optimiser against the prototype's run of the same iterations at the same voxel (`TRACE`, the run the
    trace made: `topo_free.py 7.73 <voxel> <iterations> ... --tag trace`), both on this machine's stand-in factor."""
    from zenryx.domains.gearbox.housing.optimise import run

    folder = OUT / "opt"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(TRACE / "contract.json", folder / "contract.json")
    env = {"LOOP_MEMBER_P": "40", "LOOP_LEAST_MEMBER": "8"}
    stem, _ = run("trace", 7.73, voxel, RECIPE_ARGS, folder, CONTRACT, env, iterations=iterations)
    a, b = np.load(folder / f"{stem}.npz"), np.load(TRACE / f"{stem}.npz")
    for k in sorted(set(a.files) | set(b.files)):
        if k not in a.files or k not in b.files:
            print(f"  npz {k}: only in {'src' if k in a.files else 'the prototype'}")
            continue
        same = a[k].shape == b[k].shape and np.array_equal(a[k], b[k])
        diff = float(np.abs(a[k].astype(float) - b[k].astype(float)).max()) if a[k].shape == b[k].shape and not same else None
        print(f"  npz {k}: {'identical' if same else f'largest difference {diff:.3g}' if diff is not None else 'DIFFERENT shapes'}")
    ra, rb = json.loads((folder / f"{stem}.json").read_text()), json.loads((TRACE / f"{stem}.json").read_text())
    for i, (ha, hb) in enumerate(zip(ra["history"], rb["history"], strict=False)):
        worst = _compare(_numbers({k: v for k, v in ha.items() if k not in ("seconds", "clock", "mma_seconds")}),
                         _numbers({k: v for k, v in hb.items() if k not in ("seconds", "clock", "mma_seconds")}))  # fmt: skip
        print(f"  iteration {i + 1}: the largest relative difference {worst[0]:.2e} at {worst[1]}")
    worst = _compare(_numbers(ra["binary"]), _numbers(rb["binary"]))
    print(f"  the binary check: the largest relative difference {worst[0]:.2e} at {worst[1]}")
    print(f"  frozen kg {ra['frozen_kg']!r} against {rb['frozen_kg']!r}; least kg {ra['least_kg']!r} against {rb['least_kg']!r}")


def _compare(a: dict, b: dict) -> tuple[float, str]:
    keys = sorted(set(a) & set(b))
    missing = sorted(set(a) ^ set(b))
    if missing:
        print("not in both:", missing[:20])
    rel = [(abs(a[k] - b[k]) / max(abs(b[k]), 1e-30), k) for k in keys if k not in ("unknowns",) or a[k] != b[k]]
    return max(rel) if rel else (0.0, "")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "draw"
    if what == "draw":
        draw("--prototype" in sys.argv)
    elif what == "judge":
        judge()
    elif what == "fe-glue-side":
        fe_glue_side(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]))
    elif what == "optimise":
        optimise(float(sys.argv[2]) if len(sys.argv) > 2 else 5.0, int(sys.argv[3]) if len(sys.argv) > 3 else 2)
    elif what == "fe-glue":
        fe_glue(float(sys.argv[2]) if len(sys.argv) > 2 else 16.0, float(sys.argv[3]) if len(sys.argv) > 3 else 16.0)
    else:
        args = [a for a in sys.argv[2:] if not a.startswith("--")]
        fe(float(args[0]) if args else 7.0, float(args[1]) if len(args) > 1 else 8.0)
