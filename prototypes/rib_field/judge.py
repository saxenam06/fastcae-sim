"""The toy's drawings judged by FE (LOP-34; a prototype): each drawing's watertight mesh coarsened to
`SURFACE` mm triangles (`mesh.coarse`), TetGen's quality tets (largest edge about 1.5 `SIZE`), TET10,
the bore's surface rigid with the bearing's centre where the loads act, every node in a bolt's or
the lug's column held (as the model holds them), solved in double precision (PARDISO). The same
judge for the field's ribs and for the free columns.

`judge.py <label> field|columns [--fine <mm>]`: reads `data/rib_field/<label>_field.npz` or
`<label>_columns.npz`, draws it (`draw.py`), writes `<label>_<kind>_drawn.npz` (the height map),
`<label>_<kind>.stl` and `<label>_<kind>_fe.json`.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import draw  # noqa: E402
import toy  # noqa: E402
from zenryx.domains.gearbox.housing import fe as hfe  # noqa: E402
from zenryx.physics import couplings as cpl  # noqa: E402
from zenryx.physics.tet10 import quadratic, stiffness  # noqa: E402

SURFACE = 2.0  # mm: the surface's triangles
SIZE = 3.0  # mm: the largest tet a regular one of edge 1.5 SIZE
QUALITY = (2.0, 12.0)


def judge_mesh(tm, stl: Path, say=print) -> dict:
    """FE of the drawing whose mesh is `tm`, written at `stl`: meshed by our FE's own ladder
    (`fe.mesh_tetgen`: the places TetGen names kept fine, then other sizes)."""
    import pypardiso

    e, nu, density = toy.material()
    t0 = time.time()
    nodes4, tets4 = hfe.mesh_tetgen(stl, SIZE, QUALITY, SURFACE, 1.5)
    shape = float(hfe.tet_shape(nodes4, tets4).min())
    nodes, tets = quadratic(nodes4, hfe.oriented(nodes4, tets4))
    say(
        f"meshed: {len(tets):,} TET10, {len(nodes):,} nodes, worst shape {shape:.2g} "
        f"({time.time() - t0:.0f} s)"
    )
    k = stiffness(nodes, tets, np.full(len(tets), e), np.full(len(tets), nu), gpu=False)
    skin = hfe.skin_nodes(tets)
    top = toy.WALL + toy.BAND
    seat = hfe.on_cylinder(nodes, skin, toy.BORE, toy.R_BORE, 0.0, top)
    groups = [{"nodes": seat, "ref": (toy.BORE[0], toy.BORE[1], toy.Z_LOAD), "name": "seat"}]
    for i, b in enumerate(toy.BOLTS):
        ids = np.flatnonzero(np.hypot(nodes[:, 0] - b[0], nodes[:, 1] - b[1]) < toy.R_BOLT)
        groups.append({"nodes": ids, "fixed": True, "name": f"bolt {i + 1}"})
    ids = np.flatnonzero(np.hypot(nodes[:, 0] - toy.LUG[0], nodes[:, 1] - toy.LUG[1]) < toy.R_LUG)
    groups.append({"nodes": ids, "fixed": True, "name": "lug"})
    tee, info = cpl.rigid_transform(nodes, groups)
    kr = (tee.T @ k @ tee).tocsr()
    kr = (0.5 * (kr + kr.T)).tocsr()
    rhs = np.zeros((tee.shape[1], len(toy.CASES)))
    r0 = info["ref_col"][0]
    for c, force in enumerate(toy.CASES.values()):
        rhs[r0 : r0 + 3, c] = force
    q = pypardiso.spsolve(kr, rhs).reshape(len(rhs), -1)
    compliance = float((rhs * q).sum())
    tilt = np.hypot(q[r0 + 3], q[r0 + 4])
    volume = float(tm.volume)
    out = {
        "compliance": compliance,
        "tilt_mrad": (1e3 * tilt).tolist(),
        "mass_kg": volume * density,
        "volume_mm3": volume,
        "tets": int(len(tets)),
        "unknowns": int(tee.shape[1]),
        "seat_nodes": int(len(seat)),
        "worst_shape": shape,
        "seconds": time.time() - t0,
    }
    say(
        f"FE: compliance {compliance:.2f} N mm, tilt {1e3 * tilt.max():.4f} mrad, mass "
        f"{out['mass_kg']:.3f} kg ({out['unknowns']:,} unknowns, {time.time() - t0:.0f} s)"
    )
    return out


def main() -> None:
    label, kind = sys.argv[1], sys.argv[2]
    fine = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--fine=")), draw.FINE))
    run = dict(np.load(toy.OUT / f"{label}_{kind}.npz"))
    a = float(run["voxel"])
    t0 = time.time()
    if kind == "field":
        d = draw.draw_field(run, a, fine, gate="--gate" in sys.argv)
        print(f"ribs as drawn: {d['census_before']}; kept: {d['census']}; gate: {d.get('gate')}")
    else:
        d = draw.draw_columns(run, a, fine)
    np.savez_compressed(
        toy.OUT / f"{label}_{kind}_drawn.npz",
        **{k: v for k, v in d.items() if isinstance(v, np.ndarray)},
    )
    print(f"drawn in {time.time() - t0:.0f} s")
    tm = draw.mesh(d["z"], fine)
    tm.export(toy.OUT / f"{label}_{kind}.stl")
    _, _, density = toy.material()
    res = judge_mesh(tm, toy.OUT / f"{label}_{kind}.stl")
    plate = ~d["regions"]["hole"]
    wall_kg = float(plate.sum() * fine * fine * toy.WALL * density)
    solid = d["regions"]["solid"]
    solid_kg = float(solid.sum() * fine * fine * toy.BAND * density)
    res["placed_kg"] = res["mass_kg"] - wall_kg - solid_kg
    res["drawn_placed_kg"] = float(
        ((d["z"] - toy.WALL) * (plate & ~solid)).sum() * fine * fine * density
    )
    for key in ("census", "census_before", "gate"):
        if key in d:
            res[key] = d[key]
    (toy.OUT / f"{label}_{kind}_fe.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("compliance", "tilt_mrad", "mass_kg", "placed_kg")}))


if __name__ == "__main__":
    main()
