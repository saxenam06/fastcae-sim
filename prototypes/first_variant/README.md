# First housing variant: a PROTOTYPE

**What this is.** A prototype for plan Part C, Tasks 8-11 of
[the contract v0 plan](../../docs/features/contract/2026-10-08-plan-contract-v0-and-first-variant.md).
It answers "how does the agreed geometry route work, and what does it look like?" for one
main-housing half of Hofstetter et al. 2018's two-stage reducer, made by aluminium high-pressure
die casting.

**What it is not.** It is not product code and not the judge. Nothing in `src/` imports it, and
its numbers have not passed the plan's checks. Code lives here; every output goes to
`data/prototypes/first_variant/`, which is gitignored.

## Run it

```
uv run python prototypes/first_variant/run.py
```

This takes about a minute and peaks at about 2.1 GB of memory, mostly in the thickness check.
It runs the steps in order and prints where everything landed. Each step also runs on its own,
in this order:

```
uv run python prototypes/first_variant/frontend.py        # Task 8   -> derived.json
uv run python prototypes/first_variant/field.py outline   # Task 10a -> outline.json (boss points)
uv run python prototypes/first_variant/core.py            # Task 9   -> core.step, core.stl
uv run python prototypes/first_variant/field.py           # Task 10  -> field.npz, field.stl
uv run python prototypes/first_variant/join.py            # Task 11  -> housing.stl, housing.glb
uv run python prototypes/first_variant/render.py          # Task 11  -> the seven PNGs
```

## How it works, step by step

1. **Requirement.** Hofstetter 2018, Table 2: a 165 mm input-to-output offset, a total ratio of
   9.32 ± 1 %, 366 N·m nominal input torque, 15,000 rpm maximum, 20MnCr5 gears. The bearings
   are Table 3's benchmark set.
2. **Layout and loads** (`frontend.py`, Task 8).
   - The ratio is split into 25/65 and 23/82, giving 9.270.
   - The gears are sized by rule of thumb: normal modules 2.0 and 2.5 mm, helix 20°, αn 20°,
     no profile shift. Face widths follow b = 2π·mn/sin β: 36.7 and 45.9 mm.
   - The intermediate axis sits at the vertex of the triangle (a1, a2, 165 mm), at
     (51.2, 81.0) mm.
   - Axial stations: the split face is at z = 0, stage 1 at z 5-41.7 and stage 2 at z 46.7-92.7.
     The back wall runs from z 100.7 to 105.7, and its seats start at the wall's inner face.
     L = 124.7 mm.
   - Mesh forces: Ft = 2T/d, Fr = Ft·tan αn/cos β, Fa = Ft·tan β, with directions taken from
     the mesh geometry and action = −reaction.
   - Each shaft is solved as a two-support beam, with the axial-force moment taken from the 3D
     lever arms (JTEKT eq. 5-29). Thrust goes to the locating bearing.
   - Three cases (A1): drive, regeneration and reverse.
   - Every value in `derived.json` carries its provenance.
3. **Machined core in CadQuery** (`core.py`, Task 9). This is the exact B-rep of the
   interfaces, as machined:
   - three back-wall seat rings: bore = bearing OD, 8 mm wall, a 4 mm shoulder, drafted
     outside;
   - 14 split-face bolt bosses, Ø18 with Ø9 holes and 12 mm tall, ≤ 80 mm apart along the
     shell's outline;
   - the motor-flange ring: Ø110 spigot, 6 holes on Ø130;
   - the mount pad (A4).

   The STEP file is re-imported and its volume compared.
4. **Shell and members in field space** (`field.py`, Task 10). Signed distance fields on a
   1.5 mm grid.
   - **Cavity.** The gears' keep-outs (tip + 5 mm radially, ± 3 mm axially) are swept to the
     split face, so the die's core can be drawn out, and closed by a flat back.
   - **Shell.** The band 5-10 mm outside the cavity. Its offset grows toward the split, so every
     wall tapers 2° along the pull direction +z (A7).
   - **Sealing lip** at the split face.
   - **Members.** Drafted plates, 6-8 mm thick: bridges between the seat rings, webs from each
     ring to the mount pad, radial ribs from each ring, and gussets under the motor flange.
   - **Blends.** Everything is smooth-unioned with a 6 mm blend into 0.3 mm-undersize copies of
     the core's features.
   - **Clipping.** The members are clipped to the installation space (A3). Everything is kept
     out of the keep-outs, the bearings, the shaft passages and the bolt-head room.
   - Marching cubes then gives a closed mesh.
5. **Join** (`join.py`, Task 11).
   - The field mesh and the core are united with manifold3d.
   - Every machined feature is cut again at its finished size: bores, passages, holes, the
     spigot, the flange, pad and split faces. These cutters sit 0.02 mm outside the core's own
     faces, so no two faces are coplanar.
   - The result must be one watertight body. The STL and the GLB are read back to prove it.
   - Each triangle keeps its origin: field, core or machining cutter. The draft map uses this.
   - The reported checks run on this joined part: keep-out intrusion, package, closure, voids,
     thickness and draft.
6. **Pictures** (`render.py`): `iso.png`, `split_face.png`, `section.png`, `thickness.png`,
   `draft.png`, `layout.png`, `route.png` (core, field, joined).

`params.py` holds every prototype number with its label; `layout.py` turns `derived.json` into
the geometry all the steps share.

## Rules of thumb and assumptions

- **Rules of thumb:**
  - the ratio split, modules, helix and pressure angles, zero profile shift;
  - face widths from the overlap-ratio rule;
  - helix hands chosen so the intermediate shaft's thrusts partly cancel;
  - supports at the bearings' mid-widths.

  This sizing is not a gear rating.
- **Assumptions** (spec §4.8):
  - **A1**: peak drive = regeneration = reverse = 366 N·m (the latter two reversed). The quasi-static
    seat loads for regeneration and reverse are identical, because only the torque's sign
    enters.
  - **A3**: the installation space is the layout's box grown by 20 mm.
  - **A4**: the motor flange is clamped and one torque-reaction pad is fixed.
  - **A5**: order-check speeds 7,500 and 15,000 rpm. Only the mesh-frequency list uses them.
  - **A7**: the pull direction is +z, normal to the split face.
- **Prototype choices.** Every boss, pad, flange, gap, wall, member and grid size, listed with
  its label in `params.py` and in `summary.json` under `prototype_choices`.
- **Published or catalogue values:**
  - Table 2 values;
  - the Table 3 bearing designations, with boundary dimensions from the ISO 15 series, to be
    checked against a maker's catalogue;
  - draft from NADCA 2015 §4A;
  - density 2.66 g/cm³, the card from Kim et al. 2024 via the spec (prototype).

## Where it departs from the brief, and why

- **Draft direction.** The brief says the offset grows with z. With the pull along +z and the
  opening at z = 0, that would widen the cavity toward the back wall, an undercut. So the offset
  grows toward the split instead, and the walls taper away from it.
- **Motor-flange face** is raised to z = 130.7 mm.
  - The brief's Ø150 flange (Ø130 bolt circle) reaches over the intermediate seat, whose bore
    edge is only 55.8 mm from the input axis. In plan view, the Ø110 spigot clears that bore by
    just 0.8 mm.
  - The face now sits 6 mm above that seat, and the holes are turned so the intermediate axis
    falls between two of them.
- **Bolt bosses.** The hole centres sit 10 mm outside the wall, not 5 mm, so an M8 head can
  seat. A 10 mm sealing lip carries them.
- **Installation-space clip.** The A3 box clips the members only. The bolt bosses stand outside
  it, and the volume outside is reported.
- **Frame.** +z points toward the motor, as the brief places it; the spec's default frame points
  away from it.
- **Back-wall bearings** start 8 mm behind the stage-2 faces: 3 mm keep-out plus the 5 mm gap.
- **`derived.json`** is not validated with `zenryx.contract`: this prototype stays separate from
  `src/`.

## What is NOT checked

- The front-end has not passed the plan's three load checks (spec 4.3).
- The bearing boundary dimensions are to be checked against a maker's catalogue.
- No FE yet: no stiffness, misalignment, bearing tilt, modes or stress.
- The cover half and its three seats are not built.
- Not modelled: the axial retention at the locating seats, bolt and nut seating, the sealing
  line, the tapered bearings' pressure centres and induced thrust.
- Machining stock (0.25 mm) is recorded, not modelled. There is no fill, porosity or
  parting-line study.
- The thickness map is from a 1.0 mm voxel copy, accurate to about ±1 mm. The 4 mm shoulders and
  the drafted boss walls (4.1-4.5 mm) read as just under 4 mm.

## Last run (8 Oct 2026; the numbers of record are in `summary.json`)

| Quantity | Value |
|---|---|
| Mass | 3.57 kg |
| Bounding box | 390 × 333 × 131 mm |
| Mesh | 418,654 triangles; one watertight body (manifold3d, and the STL and GLB read back) |
| Gear keep-outs, bearings, shafts | Nothing intrudes (0 mm³) |
| Closure | Closed except at the split face and the two shaft passages |
| Enclosed voids | None |
| Thickness | Min 2.8 mm, p5 4.5 mm, median 5.0 mm; 1.9 % of the area under 4 mm |
| Draft | 0.17 % of the cast area under 1° |
| Outside the A3 box | 11.6 cm³ (the bolt bosses at the ±y extremes) |
| Back-wall seat loads at peak drive | input 6206: 6.7 kN; intermediate 32010 X: 24.7 kN; output 6012: 23.7 kN |
