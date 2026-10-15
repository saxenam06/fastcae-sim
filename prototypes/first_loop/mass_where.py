"""PROTOTYPE (LOP-20) - where a drawn design holds more metal than its optimisation placed. The
optimiser's own field (the set-up's fixed voxels at their modelled mass, the placed ones as metal or
air) and the CAD voxelised (`voxel_vs_fe.voxelised`), both on one 2 mm grid, are split by region
(the thin wall, the seats, the mounts, the joint's band, the members, where the optimiser has
none), by distance from the cavity and by zone; with a picture of the extra metal (red) and the
missing (blue). On 10 October 19:46-20:58 it found the drawing's 1.9 kg (`outcome_skin_6mm_contract`).

Run: .venv/Scripts/python.exe prototypes/first_loop/mass_where.py <run stem> <design stem>
Writes data/first_loop/mass_where_<design>.png.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from topo_free import OUT, build_free  # noqa: E402
from voxel_vs_fe import voxelised  # noqa: E402

run, design = sys.argv[1], sys.argv[2]
SCRATCH = OUT  # the picture beside the run's records
FINE, RHO = 2.0, 2.6e-6  # mm, kg/mm³
cell_kg = FINE**3 * RHO

z = np.load(OUT / f"{run}.npz")
h = float(z["h"])
rec = json.loads((OUT / f"{run}.json").read_text(encoding="utf-8"))
model = build_free(h, layout=rec.get("layout", "contract"), flange=rec.get("flange", False))  # the run's own set-up
n, lo, masks = model["n"], model["lo"], model["masks"]
assert tuple(n) == tuple(z["n"]), (n, z["n"])
info = json.loads((OUT / f"{design}.json").read_text(encoding="utf-8"))
z_split, t_f = info["z"]["split"], info["settings"]["flange_thickness"]

# the optimiser's metal per voxel: each fixed voxel at its modelled share (the thin wall's, the
# split flange's), the placed ones as its metal-or-air check reads them (0.5)
flat = int(np.prod(n))
dens = np.zeros(flat)
kind = np.zeros(flat, np.int8)  # 0 nothing, 1 thin wall, 2 seats whole, 3 mounts, 4 other fixed, 5 placed
frozen_cells = z["elem"][z["frozen"].astype(bool)]
dens[frozen_cells] = np.asarray(model["mass_share"])[frozen_cells]
kind[frozen_cells] = 4
for name, k in (("wall", 1), ("seats", 2), ("mounts", 3)):
    m = np.asarray(masks[name]).ravel() & (dens > 0)
    kind[m] = k
placed_cells = z["elem"][z["free_e"]][z["phys"] >= 0.5]
dens[placed_cells] = 1.0
kind[placed_cells] = 5
rooms = np.asarray(masks["rooms"]).ravel()

# the fine grid over the same box, each cell reading its voxel
n_f = np.ceil(n * h / FINE).astype(int)
axes = [lo[i] + FINE * (np.arange(n_f[i]) + 0.5) for i in range(3)]
idx = [np.clip(((a - lo[i]) // h).astype(int), 0, n[i] - 1) for i, a in enumerate(axes)]
I, J, K = np.meshgrid(*idx, indexing="ij")
coarse = np.ravel_multi_index((I.ravel(), J.ravel(), K.ravel()), tuple(n))
X, Y, Z = np.meshgrid(*axes, indexing="ij")
centres = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
opt = dens[coarse]
cls = kind[coarse].copy()
cav = rooms[coarse]
from matplotlib.path import Path as Polygon  # noqa: E402

band = Polygon(np.asarray(info["joint_outline"], float)).contains_points(centres[:, :2]) & (np.abs(centres[:, 2] - z_split) <= t_f) & ~cav
cls[band & (cls >= 4)] = 6  # the split flange's band (where the set-up fixed nothing, or placed metal)
print(f"fine grid {n_f.tolist()} = {len(centres):,} cells; the CAD voxelised (VTK, both halves)...", flush=True)
cad = voxelised(design, centres, z_split)

names = {1: "the thin wall (4 mm in the model, one voxel)", 2: "the seats' rings (whole voxels)", 3: "the mounts",
         4: "other fixed (the bolts' bosses, the split flange)", 5: "the members the optimiser placed", 6: "the split flange's band",
         0: "where the optimiser has no metal"}  # fmt: skip
print(f"\n{'region':52s} {'optimiser':>10s} {'CAD':>8s} {'extra':>8s}  kg")
total_o = total_c = 0.0
for k in (1, 2, 3, 4, 6, 5, 0):
    sel = (cls == k) & ~cav
    o, c = float(opt[sel].sum() * cell_kg), float(cad[sel].sum() * cell_kg)
    total_o += o
    total_c += c
    print(f"{names[k]:52s} {o:10.2f} {c:8.2f} {c - o:+8.2f}")
inside_c = float(cad[cav].sum() * cell_kg)
print(f"{'inside the cavity (should be none)':52s} {0.0:10.2f} {inside_c:8.2f}")
print(f"{'all':52s} {total_o:10.2f} {total_c + inside_c:8.2f} {total_c + inside_c - total_o:+8.2f}   (the CAD's own: {info['mass_kg']['total']:.2f} kg)")

# The CAD's metal where the optimiser has none, by its distance from the model's cavity: within
# a voxel it is the wall drawn thicker or further out than the model's one-voxel skin; further
# out, the members grown by the fairing and the smoothing, and the fillets
from scipy.ndimage import distance_transform_edt  # noqa: E402

d_cav = distance_transform_edt(~cav.reshape(tuple(n_f))).ravel() * FINE
none = (cls == 0) & ~cav & cad
print(f"\nthe CAD's {none.sum() * cell_kg:.2f} kg where the optimiser has no metal, by distance from the model's cavity:")
for a, b in ((0, 6), (6, 12), (12, 24), (24, 1e9)):
    sel = none & (d_cav > a) & (d_cav <= b)
    print(f"  {a:>3g}-{b if b < 1e9 else '':>3} mm: {sel.sum() * cell_kg:5.2f} kg")
near_member = distance_transform_edt(~((cls == 5) & ~cav).reshape(tuple(n_f))).ravel() * FINE
far = none & (d_cav > 6)
print(f"  of the {far.sum() * cell_kg:.2f} kg beyond 6 mm: within 2 mm of a member {(far & (near_member <= 2)).sum() * cell_kg:.2f}, "
      f"2-4 mm {(far & (near_member > 2) & (near_member <= 4)).sum() * cell_kg:.2f}, further {(far & (near_member > 4)).sum() * cell_kg:.2f}")

# Two zones, whatever kind of metal: the wall's (within 9 mm of the model's cavity, a voxel and a
# half) and beyond it (the members, the flange's band, the mounts), and the model's cavity itself
print("\nby zone:                                  optimiser      CAD    extra  kg")
for label, sel in (("the model's cavity voxels", cav), ("the wall's zone (within 9 mm of the cavity)", ~cav & (d_cav <= 9)),
                   ("beyond it (members, flange, mounts)", ~cav & (d_cav > 9))):  # fmt: skip
    o, c = float(opt[sel].sum() * cell_kg), float(cad[sel].sum() * cell_kg)
    print(f"  {label:44s} {o:8.2f} {c:8.2f} {c - o:+8.2f}")

# Where: the extra and the missing metal per voxel, over the CAD
import pyvista as pv  # noqa: E402

pv.OFF_SCREEN = True
cad_c = np.bincount(coarse, weights=cad.astype(float), minlength=flat) / max(1, int((h / FINE) ** 3))
diff = cad_c - dens
extra, missing = (diff > 0.5) & ~rooms, (diff < -0.5) & ~rooms
grid_pts = np.column_stack(np.unravel_index(np.arange(flat), tuple(n))) * h + lo + 0.5 * h


def cubes(sel):
    pts = pv.PolyData(grid_pts[sel])
    return pts.glyph(geom=pv.Cube(x_length=h, y_length=h, z_length=h), scale=False, orient=False) if sel.any() else None


p = pv.Plotter(shape=(1, 2), window_size=(1800, 850), off_screen=True)
for col, (view, title) in enumerate((((0.35, -0.55, 0.75), "from the cover's side"), ((-0.35, -0.55, -0.75), "from the motor's side"))):
    p.subplot(0, col)
    placed = cubes((kind == 5) & ~extra)
    if placed is not None:
        p.add_mesh(placed, color=(0.80, 0.82, 0.85), opacity=0.25)
    for sel, colour, label in ((extra, (0.85, 0.25, 0.20), "extra in the CAD"), (missing, (0.20, 0.40, 0.85), "missing in the CAD")):
        c = cubes(sel)
        if c is not None:
            p.add_mesh(c, color=colour, label=label)
    p.view_vector(view, viewup=(0.0, -1.0, 0.0))
    p.add_text(f"{design}: red = more metal than the optimiser's (by more than half a voxel), blue = less; grey = its members ({title})", font_size=9)
p.screenshot(str(SCRATCH / f"mass_where_{design}.png"))
print(SCRATCH / f"mass_where_{design}.png")
