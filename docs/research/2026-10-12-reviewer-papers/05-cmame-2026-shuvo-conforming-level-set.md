# Shuvo et al. 2026: level-set optimisation on conforming meshes, then damage-informed refinement

12 October 2026, 19:57. Read for the reviewer's proposal: a 3D level-set boundary over the whole permitted volume, with smoothness, thickness and casting rules inside the loop, keeping the optimised solid as the design.

## 1. Citation and reading

Shuvo M.S., Sheldon A., Vemparala B., Ghosh A., Shirazi M., Soghrati S. (2026). Automated level-set topology optimization with conforming meshes and damage-informed morphological refinement. *Computer Methods in Applied Mechanics and Engineering* 461, 119252. doi:10.1016/j.cma.2026.119252. Online 29 July 2026; open access, CC BY-NC-ND 4.0; funded by Honda Research Institute USA. Soghrati's laboratory, Ohio State University.

**Not read in full: the figures and a paraphrased abstract only.**
- ScienceDirect met WebFetch, curl with a browser agent and headless Edge with a bot challenge (HTTP 403). Elsevier's API gives only metadata without a key. No arXiv preprint; OpenAlex lists no repository copy.
- **Read:** the metadata; the abstract as a search engine's paraphrase; all 30 figures at full size from Elsevier's figure server, with the numbers printed on them.
- **Not seen:** captions, text, equations, tables, stated limitations. Every number below is read off a figure. Which runs are stress- or volume-constrained, and the material, are my inferences.

## 2. Problem and representation

- **Problem** (abstract, figures): linear-elastic 2D structures and one 3D beam; the least volume under a stress limit, or the least stress under a volume limit. Stress is the p-norm of von Mises (Fig. 5).
- **Design variable:** a level-set function Φ on a fixed structured grid; metal where Φ < 0.
- **What is analysed:** each iteration, Φ's zero contour becomes closed NURBS curves, and the mesh is built on them: the analysed boundary is the design's.
- **Second stage:** damage simulations of chosen layouts, then local NURBS edits where cracks start.

## 3. The method (Figs. 3-6)

- Φ advected by explicit forward Euler; re-initialised every 5 iterations.
- The zero contour fitted by NURBS with fewer control points (Fig. 3a); "floating islands" flagged (Fig. 3b), presumably deleted.
- A conforming triangle mesh by CISAMR, the group's in-house C++ mesher: a structured grid refined near the boundary, nodes moved onto it, cut cells split (Fig. 4).
- Elasticity in FEniCS; the shape derivative computed on that mesh and projected onto the level-set grid.
- Every run starts from a regular array of seeded holes.
- **Stage 2:** an elastoplastic damage simulation in ABAQUS; yield point, peak force and toughness read off the force-displacement curve; at the boundary where the main crack starts, control points pushed outward by a cosine bump (amplitude a, width b); remesh; repeat until converged or a maximum count (22 designs in one case).

## 4. What it controls, and what it does not

**Controls:** the boundary's accuracy in the analysis (no grey or stair-stepped elements, Fig. 9); smoothness, through the representation only (few control points, re-initialisation); stress peaks (the L-bracket's re-entrant corner comes out rounded, Figs. 10, 14); some topology change (holes merge or close).

**Does not control** (nothing visible in the figures or the abstract):
- curvature or perimeter as a penalty;
- least or greatest member size: members run from thin struts (L4) to a solid block (L6, Fig. 15);
- junction size: round hubs at the crossings (Figs. 12-13);
- any casting rule: pull, draft, undercut, parting line;
- hole nucleation: the topology follows the seeding (Fig. 12: three seedings, three topologies) and the level-set grid (Fig. 13);
- feature types: no plates, ribs or bosses;
- stiffness, displacement or modes; one load case an example;
- mass in stage 2: it only adds metal.

## 5. Scale and cost

- **2D:** a 2 × 1 cantilever with a tip load; a 1 × 1 L-bracket with 0.4-wide arms. Damage meshes on background grids of 52 × 26 to 202 × 101 and 50 × 50 to 150 × 150 cells.
- **3D:** one 2 × 1 × 0.4 beam (an edge fixed, an edge pinned, a mid-span load), shown meshed (Fig. 26). Size and run time not visible; no 3D damage stage.
- **Runs:** cantilever 42-85 iterations in 11-22 min; L-bracket 450-804 iterations in 120-639 min: 15-48 s an iteration, in 2D.
- **Time split** (Fig. 11b): meshing 56.3 %, FE 31.1 %, shape derivative 4.3 %, other 8.3 %. Hardware not visible.

## 6. Results

- **Conforming against pixelated mesh** (L-bracket, Figs. 10-11): highest von Mises 61 against 69; the conforming run stopped near iteration 310, the pixelated one ran to 1,256.
- **Cantilever, five seedings or grids:** highest von Mises 36.1-36.4 at volume fractions 0.54-0.60, each a different topology.
- **L-bracket, six runs:** 39.3-83.4 at volume fractions 0.59-0.19.
- **Stage 2**, percent change from first design to last:

| | Volume | Yield point | Peak force | Toughness |
|---|---|---|---|---|
| Cantilever C1-C5 (Fig. 20) | +1.2 to +4.2 | +0.6 to +20.7 | +12.1 to +51.2 | +165 to +206 |
| L-bracket L1-L6 (Fig. 25) | +4.2 to +56.6 | +38.6 to +246.3 | +14.1 to +371 | +105 to +625.6 |

- One cantilever: seven designs, volume fraction 0.560 to 0.572, peak force about 3.9 to 6.1 × 10⁷ N (Fig. 17). Another took 22 designs, its crack moving between support and load (Fig. 18).
- The damage curves agree on three grids up to the peak (Figs. 28, 30).

## 7. Limitations

**Stated:** not seen.

**What I see:**
- 2D but for one 3D demonstration, and 2D runs already take up to 10.6 hours, mostly meshing.
- No equal-mass comparison is visible for stage 2: L4 gained 56.6 % volume.
- The optimiser knows only linear stress, so the damage stage finds what it ignored.
- Huge deformations: 0.5-1.5 m on a 2 m cantilever, von Mises up to 530 MPa. The toughness counts large plastic flow, which a casting alloy of a few percent elongation would not show.
- Stage 2 is a heuristic: a bump at each crack, no gradient; it chases the next weak spot.

## 8. Code and data

None found in the lab's publication list or by search. The mesher is "in house C++" (Fig. 5); FEniCS is open source; ABAQUS is commercial. Reproducing it needs both.

## 9. For our problem

**Would it cure the irregular shape? No.**
- Its designs are organic trusses too: members of varying width, hubs at crossings, a block in L6. A body-fitted boundary makes surfaces smooth, not members regular, straight or plate-like.
- Our lumps, knots and wavy sides are in the metal's layout, not in stair-steps; our size and perimeter rules left them. The paper adds nothing stronger.

**Would it keep stiffness? Yes, in the way that matters to us.**
- The analysed solid is the design; nothing is redrawn. Our losses came from redrawing (2-5 times softer) and from the voxel model flattering thin members (FE reads them 11-30 % softer, hence the optimiser's 1.15 factor). A conforming loop removes both by construction.
- Stage 2 only adds metal, so it cannot lose stiffness; our cleanings moved or removed it.

**The reviewer's proposal:**
- **Supported:** keep the optimised solid as the design; analyse the exact boundary inside the loop; smooth boundaries from a sparse spline, without a penalty term.
- **Warned against:** a level set keeps the topology it was seeded with. Over the whole permitted volume it needs a way to open holes (a topological derivative); none here.
- **No evidence:** curvature penalties, thickness and junction rules, casting rules, plate or branch rules.
- **No fixed shell:** a seeded level set would open holes in the housing's walls; the paper has no rule for a closed, oil-tight skin.

**What it would take us:**
- **A mesher in the loop.** CISAMR is not public, as far as I found. TetGen (ours) or mmg's level-set mode (open source) could serve, or a mesh morphed to the boundary (LLNL, doi:10.1007/s00158-024-03870-3, not read). One flat tet stops our single-precision factor; a remesh every iteration multiplies that risk.
- **Size:** 412,667 TET10 (2.18 M unknowns) is the card's ceiling: 300k elements fit, 1M only as linear tets.
- **Derivatives:** each seat's tilt and bed displacement (an adjoint per seat and case), velocity extension, re-initialisation: two to three weeks for a robust 3D version in Python and CuPy (my estimate).
- **Time:** our FE judge takes 78-219 s a design (mesh, solves, modes, both halves). If a static cycle took 30-70 s, the L-bracket's 450-804 iterations would take 4-16 hours a run, against 231 s for today's whole optimisation (`it1_free_5.5kg`).
- **So:** a short polish after the density run, not the optimiser.

**The first test:**
1. **One hour:** on one half, remesh a level-set surface with TetGen at 4 and 2 mm, solve peak drive, compute the compliance shape derivative; repeat on 20 slightly moved surfaces, counting refusals and flat tets. Over 60 s a cycle, or one failure in 20: no conforming loop.
2. **Two to three days:** a 30-iteration conforming polish of `it1_free_5.5kg` (5.63 kg, 37 µm, tilt 0.93 ×): one half, topology fixed, mass held, with and without a mean-curvature term; judged and graded as usual. Pass: bed and tilt within 3 % at equal mass, and fewer lumps (`look.py`). If the curvature term costs stiffness, smoothing inside the loop fails here too.

**Later, perhaps:** stage 2's loop (simulate, find the weak spot, add a local bump, judge again) suits strength cases such as a mount's abuse load, where added metal is the answer. It is not a stiffness tool.

## 10. Sources

- The article page (HTTP 403, not read): https://www.sciencedirect.com/science/article/pii/S0045782526005256
- Metadata: https://api.crossref.org/works/10.1016/j.cma.2026.119252 ; https://api.openalex.org/works/doi:10.1016/j.cma.2026.119252 ; https://api.elsevier.com/content/article/PII:S0045782526005256?httpAccept=text/xml
- Figures 1-30: https://ars.els-cdn.com/content/image/1-s2.0-S0045782526005256-gr1_lrg.jpg to `-gr30_lrg.jpg`
- The lab's publication list: https://mae.osu.edu/acml/publications
- The abstract: two web-search summaries of the indexed article page (no URL given).
- Our numbers: `data/first_loop/grade_it1_free_5.5kg.log`, `flow_it1_free_5.5kg.json`, `flow_p40_free.json`, `flow_p40_clean.json`; CLAUDE.md (the FE ceiling, the 1.15 factor's reason).
