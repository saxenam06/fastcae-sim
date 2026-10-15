# Production EV gearbox housings against our designs (11 October)

**Asked** by the engineer, 07:32-07:33:
> compare the pictures of CAD with the pictures of ribs I gave you of production housing; what issues do you see? No fillets? Or production ribs are that high? The CAD still looks very odd. What are we missing? What further constraints can we bring into the optimisation?

and

> search a few images of production housing of EV gearbox on the web and compare.

**Read with:** [production housings against ours](2026-10-09-production-housings-against-ours.md) (9 October: the engineer's 36 pictures, the trade's grammar in §2.5, the rule values with their sources in §5.4).

**The photos:** four sources found today, listed in section 6. They are third-party images, so they stay in the session's scratchpad and are not committed. The side-by-side sheet, with our two designs, is `data/first_loop/compare_production_housings.png`.

## 1. What the production housings show

1. **An HPDC EV gearbox and motor housing** (Anhui Gaojian; cast on a 1,250 t machine):
   - thin fins run along the pull up the motor bore's cylinder, at an even pitch, each one ending at the top flange and swept into the base as a gusset;
   - a perimeter flange carries bolt bosses at a regular pitch, with ears and gussets, and port bosses;
   - every root and edge is filleted.
2. **The same maker's housing, seen face on:** low ribs form one network:
   - spokes run from a raised ring round the large bore to the rim, with a concentric arc;
   - a rectangular grid and diagonals cover the flat panel, with small round nodes where ribs cross;
   - bolt bosses sit on the rim.

   Every rib ends on a ring, a node, a boss or the rim.
3. **A cast reducer housing with three bores, a two-stage reducer like ours** (Metcast):
   - each bore sits in a thick boss, its face machined flat in one plane;
   - triangular gussets run from the flange's bolt bosses into the body, beside mount pads;
   - the shell is smooth and curved round the gears;
   - the ribs are few and short, and there are no tall webs.
4. **An HPDC gearbox shell** (*Materials* 14:3999, 2021, open access):
   - AlSi9Cu3, 456 × 381 × 275 mm, 9.9 kg;
   - the average wall is 4 mm, locally over 9 mm (its wall-thickness map: walls 4-5 mm, ribs and bosses 6-9 mm only where they join);
   - each bore has a boss ring with spokes (a wheel), with ribs between the bosses and a boss at every bolt and port.

They share the grammar of 9 October (§2.5):
- one smooth shell round the gears;
- **hard points first:** bosses at the bores, bolt bosses at a pitch, ears;
- **ribs between hard points:** wheels on round faces, grids on flat panels, gussets at every overhang;
- **ribs thinner than the wall and low,** of one thickness and depth in a family, drafted, filleted at the root and rounded on top;
- every rib ends on something.

## 2. Ours, measured

On `outcome_c_6mm_drive`, the ribbed CAD of flow C, from its record (`scratchpad/rib_heights.py`):

| | Ours | Production |
|---|---|---|
| Rib height off the shell beneath | median 63-64 mm; 10-90 %: 26-103 mm; up to 105 mm | low: by eye about 10-25 mm on end faces, fins about 20 mm |
| Rib thickness | 12 mm, 3 × the 4 mm wall | thinner than the wall (0.8 × wall, §5.4); about 3-5 mm by eye |
| Height over thickness | median 6.2-6.7, up to 12.7 | about 3-5 by eye |
| Rib length | median 38-47 mm: short stubs | long, boss to boss, boss to rim |
| Where a rib ends | often in the open (the field's centre-line stops) | always on something |
| Bosses at the bores | none (not in the agreed set-up since 10 October 19:24) | a thick boss at every bore, its face machined |
| Gussets at the bolt bosses | none | at every bolt boss and ear |
| Fillets | none | everywhere: R 1-1.25 × the thinner leg at a T (§5.4) |
| Draft | 0° (the contract's A11, printed moulds) | 1-2° (die casting; §5.4) |
| Rib tops | wavy: they follow the field's members' ends | flat or one straight slope a family |
| The network | the field's skeleton: irregular, angles anywhere | radial, concentric, grid; even pitch |

Flow B's organic members are worse still to the eye: deep webs and lumps standing on the walls.

## 3. Why ours look odd

1. **The design space reaches about 100 mm past the end walls,** to the packaging's limit, and a member's bending stiffness grows with the cube of its depth. Under a mass budget the optimum is therefore a few deep webs: the field placed members 20-100 mm proud. Nothing in the set-up says what production's rule says: a rib stands no higher than the bosses it meets, and the outside hugs the shell.
2. **The greatest member is 12 mm, three times the wall.** A production rib is thinner than its wall, because a thicker one makes a hot spot (§5.4). At 6 mm voxels the optimiser cannot make a 4 mm rib: its least member is one voxel.
3. **There are no hard points to run between:** no bosses at the bores, no gussets at the bolt bosses. The members end where the field's density ends, and so do the ribs read from them.
4. **The drawing has none of the casting detail:**
   - no fillets, no draft;
   - square rib ends;
   - tops that follow the field's members' ends;
   - polygon steps round the pads.
5. **The reading is mechanical.** It draws what the field holds, not the trade's grammar: hard points first, ribs between them, wheels and grids, families of one thickness and depth. The engineer said as much on 10 October: "nowhere close".

## 4. Constraints the optimisation can take (proposals)

| Constraint | What it changes | How, in `topo_free.py` | Cost |
|---|---|---|---|
| **A height envelope:** metal only within H of the shell (20-25 mm, or the bosses' height) | no deep webs; the members spread over the shell as low ribs and plates | the free voxels beyond the offset kept out, in the set-up | none: fewer voxels, a faster run |
| **Bearing bosses and the flange's gussets as hard points** | ribs have something to run between; the seats carry production's boss | fixed voxels in the set-up; a contract entry (A26's joint rules hold the flange; the bosses would join them) | small; **the engineer's call** (a contract change) |
| **Members no thicker than the wall** | ribs, not slabs, and no hot spots | the greatest member at 6-8 mm on 3-4 mm voxels; at 6 mm voxels the least member is 6 mm | 4 mm voxels: about 3.4 × the voxels, about 15 minutes a run |
| **A mode margin** | no mode within 3 % of a gear-mesh order (every flow B design fails this one line) | the modes' eigenvalues as GCMMA constraints, their derivatives from the mode shapes | an eigensolve an iteration |
| **The pull, already held** | nothing to change: the split route's casting filter | - | - |

In the drawing, not the optimisation:
- fillets: R 1-1.25 × the rib at its root, tops fully rounded (grammar.py's swept pill section);
- one thickness and one depth for each rib family, with straight tops;
- the process's draft;
- the ribs read onto a graph between the hard points (the trade's grammar, LOP-9's `grammar.py`), the field choosing which edges carry metal.

## 5. Order

1. **The height envelope** (no contract change): one run of 5 minutes, then look at whether the members become low ribs on the shell.
2. **The bosses and gussets as hard points:** the engineer's decision.
3. **The reading as the trade's grammar,** fillets and families drawn, sized by FE.
4. **The mode margin.**
5. **4 mm voxels,** once the form looks right.

## 5b. The evening: the height-field design against 17 more pictures (17:53-18:24)

The engineer sent 17 more pictures (ZF's rail axle drives, Kalyani's and Punch's EV reducers, Avtec's, Rawsuns', a paper's modification model); they stay out of git. Against `outcome_hf6_4mm_7.0kg`, the first design to pass every graded line from a continuous height field, measured on its own continuous heights (`scratchpad/member_census.py`):

| | Ours | Production |
|---|---|---|
| The shell's plan under members | motor side 48 %, cover 42 % | about 10-25 % of a face, by eye |
| Member width on its centre-line | median 13-14 mm; 10 %: 6 mm; 90 %: 34-41 mm; at most 67-86 mm | 4-6 mm, one thickness a family |
| Height off the shell | median 14-19 mm, a third at the envelope's 24 mm | 10-25 mm |
| Where a member ends | it blends into the next | on a boss, a ring, the rim or another rib |

The engineer's verdict: "like someone has spilled a thick paint on the housing". The cause is the optimisation, not the drawing: its plan filter (6 mm) and 4 mm voxels allow little narrower than 6 mm, under the 24 mm envelope it spreads its metal sideways, and nothing asks for production's families. What followed:[the chained optimisation](../features/product/2026-10-11-chained-optimisation.md) (D15).

## 6. Sources

- Anhui Gaojian Machinery Technology, "New energy vehicle gearbox housings", Euroguss exhibitor page: https://www.euroguss.de/en/exhibitors/anhui-gaojian-machinery-technology-co-ltd-2510421/new-energy-vehicle-gearbox-housings-2531140 (photos at images.nuernbergmesse.de).
- Metcast Co., "Gearbox housing", Euroguss exhibitor page: https://www.euroguss.de/en/exhibitors/metcast-co-ltd-2509846/gearbox-housing-2531797.
- "Die Casting Die Design and Process Optimization of Aluminum Alloy Gearbox Shell", *Materials* 14:3999 (2021), open access: https://pmc.ncbi.nlm.nih.gov/articles/PMC8303643/ (Figs 1-2: the shell and its wall-thickness map; the text: 4 mm average wall, over 9 mm locally, 9.9 kg, AlSi9Cu3).
- The rule values and their sources: [production housings against ours](2026-10-09-production-housings-against-ours.md), §5.4.
