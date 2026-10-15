"""A drawn design judged by the product's own stages, on this machine (LOP-34; a prototype):
`judge.py <design> [--folder=<dir>] [--most=<unknowns>] [--skip=fe,castable,look]`.

The oil-tight gate (`oiltight.check`), FE (`fe.judge`: on the CPU through the GPU stand-ins of
`checks/support/gpu_on_cpu`, PARDISO in double), castability (`castable.castability`), the grade
(`zenryx.workflow.grade.grade_all` over the folder) and the pictures (`look.look`). The container
holds 15 GB, so FE's mesh is held under `--most` unknowns (1.2 M by default: `fe.MESHED_MOST`, the
surface coarsened by FE's own ladder); judge the reference the same way to compare like for like.
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

MOST = 1_200_000


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    design = args[0]
    opt = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    folder = Path(opt.get("folder", housing.OUT))
    most = int(opt.get("most", MOST))
    skip = set(filter(None, opt.get("skip", "").split(",")))
    from zenryx.domains.gearbox.housing import castable, fe, look, oiltight
    from zenryx.workflow import grade

    fe.MESHED_MOST = most
    times, result = {}, {"design": design, "folder": str(folder), "meshed_most": most}
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
    (folder / f"judged_{design}.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
