"""A drawn design judged by the product's own stages, on this machine (LOP-34; a prototype):
`judge.py <design> [--folder=<dir>] [--most=<unknowns>] [--skip=fe,castable,look] [--no-coarse]`.

The oil-tight gate (`oiltight.check`), FE (`fe.judge`: on the CPU through the GPU stand-ins of
`checks/support/gpu_on_cpu`), castability (`castable.castability`), the grade
(`zenryx.workflow.grade.grade_all` over the folder) and the pictures (`look.look`). The container
holds 15 GB, so FE factorises as the product does, in single precision refined to double, with
PARDISO's symmetric factor (`symfactor.py`), its mesh held under `--most` unknowns (the product's
2.18 M by default) and kept (`fe_mesh_<design>_<most>.pkl`); judge the reference the same way.
Writes into the folder (`data/rib_housing` by default) what each stage writes, and
`judged_<design>.json`: what ran, each stage's time, the grade's row.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import housing  # noqa: E402

MOST = 2_180_000  # the product's own ceiling (`fe.MESHED_MOST`), with the symmetric factor (`symfactor`)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    design = args[0]
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    folder = Path(opt.get("folder", housing.OUT))
    most = int(opt.get("most", MOST))
    skip = set(filter(None, opt.get("skip", "").split(",")))
    from zenryx.domains.gearbox.housing import castable, fe, look, oiltight
    from zenryx.workflow import grade

    import pickle

    import symfactor

    symfactor.use()  # the product's single factor on the CPU: PARDISO's, symmetric, in single
    fe.MESHED_MOST = most
    # FE's mesh kept beside the design (git-ignored data), so a judgement retried costs no meshing
    mesh_of = fe._mesh
    cache = folder / f"fe_mesh_{design}_{most}.pkl"

    def cached_mesh(info, out, size, surface):
        if cache.exists() and cache.stat().st_mtime > (out / f"{design}.json").stat().st_mtime:
            print(f"FE's mesh from {cache.name}", flush=True)
            return pickle.loads(cache.read_bytes())
        got = mesh_of(info, out, size, surface)
        cache.write_bytes(pickle.dumps(got, protocol=pickle.HIGHEST_PROTOCOL))
        return got

    fe._mesh = cached_mesh
    surface = "FE's own (decimated to its surface ladder)"
    if "--no-coarse" in sys.argv:
        # a design already remeshed at FE's scale (`remesh.py`) goes to TetGen as it is: FE's
        # decimation folded the rib drawings' surfaces (`rib_h3`), and the remesh leaves nothing to
        # decimate
        import numpy as np

        from zenryx.domains.gearbox.housing import mesh as mr

        mr.coarse = lambda tm, edge, keep_near=None: (np.asarray(tm.vertices, float),  # noqa: ARG005
                                                      np.asarray(tm.faces, np.int64))
        surface = "remeshed, not decimated"
    times, result = {}, {"design": design, "folder": str(folder), "meshed_most": most, "surface": surface}
    t = time.time()
    result["oiltight"] = bool(oiltight.check(design, folder, housing.CONTRACT)["tight"])
    times["oiltight"] = time.time() - t
    print(f"oil-tight: {result['oiltight']} ({times['oiltight']:.0f} s)", flush=True)
    if "fe" not in skip:
        t = time.time()
        fe.judge(design, folder, housing.CONTRACT)
        times["fe"] = time.time() - t
        print(f"FE in {times['fe']:.0f} s", flush=True)
    if "castable" not in skip:
        t = time.time()
        castable.castability(design, folder, housing.CONTRACT)
        times["castable"] = time.time() - t
    grades, _ = grade.grade_all(folder, housing.CONTRACT)
    row = next((g for g in grades if g.get("stem") == design), None)
    result["grade"] = row
    if row is not None:
        print(grade.table([row]), flush=True)
    if "look" not in skip:
        t = time.time()
        look.look(design, folder)
        look.look(design, folder, face=True)
        times["look"] = time.time() - t
    result["seconds"] = times
    result["factors"] = symfactor.MEMORY_REPORT  # PARDISO's memory (KB) and times, factor by factor
    (folder / f"judged_{design}.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
