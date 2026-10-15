# A reviewer's direction and five papers, read against our problem

**12 October 2026, 20:15.** At 19:36 the engineer sent a reviewer's direction (pasted text) and five links, and asked how I read them. At 20:04 they added their own diagnosis: the parametric shell and the optimiser's organic shapes come from two worlds and look bad together; start from an empty design space, or keep the shell minimal (0.5 mm), or build the shell as an approximated function in the same space. The aim is one elegant shape that a CAD designer can accept and build CAD from.

Each paper was read by its own agent, and each wrote a note in [2026-10-12-reviewer-papers/](2026-10-12-reviewer-papers/). This page is the reading across them.

## 1. The reviewer's direction

**What it proposes:**
- Optimise a full 3D implicit boundary (a level set, signed distance or neural field) over the whole permitted volume.
- Inside the loop:
  - curvature or surface-complexity penalties;
  - local-thickness and junction-size constraints;
  - casting constraints (pull and draft);
  - "adaptive geometric rules": plate-like, bounded-thickness members in slender regions, and 3D branching near load introduction such as the mount brackets;
  - a way to change topology.
- Keep the optimised solid as the design, and label its features for the CAD engineer.
- Do not smooth the old result, and do not rebuild its skeleton as ribs.

**Where our evidence agrees:**
- **Rules inside the run.** Every clean-up after a run lost 2-5× in stiffness:
  - the skeleton (`a2_b1`): 172 µm against 36.8;
  - the clean members (`p40_clean`): 81.7 against 39.4;
  - the parametric CAD (`param5`): 239.
- **Keep the solid.** Faithful redraws keep stiffness (rho2sdf: about 8 %; Amroune: 2-11 %), and simplified ones lose it.
- **The whole permitted volume.** That is the engineer's D16 (the design space fixed in every iteration), and their wish to start empty.
- **Judge the final solid.** That is our practice already.

**It reads our height field correctly:** one run of metal per column, standing on a fixed shell, smoothed over 6 mm in plan, inside a 24 mm band.

**What is not proven:**
- That a smooth 3D boundary with thickness rules produces production ribs and organic brackets together. None of the five papers shows it, and the reviewer concedes that "a smooth 3D level-set field alone will not guarantee either one".
- **The vague part is the crux:** where the rules turn from "plate-like" to "branching". A concrete form would be a greatest-member limit that varies with distance from the load interfaces: tight across the walls, looser near the mount eyes and bores, and fixed for the whole campaign (consistent with D16).

**What it leaves out:**
- **Oil-tightness without a shell.** A free field over the whole volume will not close the housing round the gears, because stiffness has no reason to.
- **Resolution.** Production's ribs are 4-6 mm thick, and our voxels are 4 mm.
- **Cost.** A conforming level set would take 4-16 hours a run on this laptop (note 05), against about 4 minutes for today's optimisation.
- **The modes.** Our designs clash with the gear orders by chance.

## 2. The five papers

| # | Paper | How read | What it is | For us |
|---|---|---|---|---|
| 01 | Li, Qin, Wei, Su 2022, IJNME 123, doi 10.1002/nme.6851: boundary density evolution | The paper itself refused (Wiley 403); read through the authors' patent CN112100882B, their 2024 follow-up and three citing papers | A density method with a deletion schedule; the smooth boundary is a strain-energy contour drawn once, after the run | Keeps the layout; no rule of any kind; its 3D bridge comes out lumpy. Nothing to take |
| 02 | Amroune, Cuillière, François 2022, CAD 145, 103183: lofting along the skeleton | In full | Skeleton, ray sections, B-spline lofts, junction patches | Compliance within 2-11 % because it copies the shape as it is (the bridge lost 5.6 % of its volume and 35 % of its stiffness by peak displacement). Beam-like only. Flat sections sampled by rays keep 7-79 % of their bending stiffness (our check). It explains our skeleton rebuilds' loss: we simplified. Take its validation protocol (mass ratio beside stiffness ratio) and a per-member read-out for the CAD designer |
| 03 | Radler et al. 2025, arXiv 2502.13174 (GenTO, renamed TOM in v2) | In full (v1 and v2), with the released code | SIMP driven by a neural field (WIRE); several designs from one run by a diversity constraint | Wavy by the authors' choice, with no length scale or rule. Mean compliance +10 % / +17 % / +32 % against plain SIMP; one 3D case at 16,770 elements. From an empty envelope its bracket is organic, dimpled plates and arms. **Our note of 13:42 had v1's numbers and called it smooth by construction: both wrong** |
| 04 | Wang, Ma 2026, CAGD 127, 102557: Catmull-Clark subdivision | In full, with the figures | A smooth subdivision surface fitted to the result after the run, with an optional Gauss-curvature fairing | Keeps the layout; plates come out as tubes; the numbers are inconsistent (the bridge 4× stiffer, unexplained). One idea, untested: Gauss curvature as a smoothness measure (zero on planes and cylinders, high on lumps and saddle-shaped knots) |
| 05 | Shuvo et al. 2026, CMAME 461, 119252: level set on conforming meshes | Figures and a paraphrased abstract only (ScienceDirect 403) | A stress-based level set; each iteration's boundary is meshed exactly (NURBS, an in-house mesher); then local refinement where damage starts | The analysed solid is the design, so nothing is lost redrawing it. But its designs are organic trusses, with no thickness, casting or closed-wall rules and no hole nucleation. 2D runs take up to 10.6 hours. For us, a polish at most |

**What they add up to:**
- **Four of the five are post-processing or rebuilding:** 01, 02 and 04 here, and rho2sdf ([note](2026-10-12-smooth-extraction-rho2sdf.md)). They keep the optimiser's layout, so they cannot change the look.
- **The other two optimise:**
  - the neural field is less stiff and wavy;
  - the conforming level set is accurate but organic and slow.
- **None handles casting or a closed wall,** and none shows regular ribs emerging beside organic brackets.
- **So the elegance has to come from our own rules inside the optimisation.** The reviewer's direction is a hypothesis to test, not established practice.

## 3. The engineer's two worlds

**The diagnosis holds.** A crisp, CAD-made shell (lobed cylinders, flat end walls, a flange land) carries organic metal from the optimiser, and the eye reads two objects: paint on a housing. The rho2sdf paper's gripper shows the same clash between a crisp box and an organic body.

**The fixed shell also causes the paint:**
- The optimiser can only add metal on top of a fixed 4 mm wall, column by column.
- Where the structure wants a thicker wall (the end walls under the bearings), it can only spread a layer over it.
- If the wall is the optimiser's, the same need shows as a smoothly thicker wall: one body, no layer on top.

**The three options:**
- **Start empty:** the cleanest way to one design language.
- **A 0.5 mm shell:** cannot be geometry. It cannot be cast (the contract's `min_wall` is 4 mm), and FE stops on faces under about 0.5 mm in single precision. As a rule it equals starting empty: the optimiser must close the housing, where and as thick as it chooses.
- **The shell as a function in the same space:** right, and strongest as that rule (the enclosure). Today's fixed shell drawn inside the same field would end the clash in the drawing, but keep our form and the paint on it.

**The drawing rule for one casting:**
- every as-cast surface from the one field, smooth;
- exact only the faces a machine cuts: bores, the joint face, mount faces, bolt and seal holes.

This is how real castings look, and it is what a CAD designer starts from: exact datums, and a smooth cast body to trace, labelled by member (walls, ribs, bosses, brackets).

**What starting empty costs:**
- **The enclosure rule:** every path out of the gear rooms must cross at least the least wall of metal. It is new; no paper here has one. A watertightness check on the drawn solid goes with it.
- **Walls at the voxel's scale:** about two voxels (8 mm at 4 mm), twice today's exact 4 mm wall. The alternatives are a wall modelled finer than a voxel (as the flange is, at the share of each voxel it fills) or 3.5 mm voxels.
- **The look:** organic, in the generative-design style. One world, but elegant only if the rules keep it smooth and legible.
- **The joint:** bonded at the split for a first look; the sealing land (A26) and bolts after.
- **The 24 mm envelope:** it was measured off the shell, so it lapses. Tall webs may return (they did on 10-11 October); the greatest member must keep lumps out.

## 4. The proposal

**Start from an empty design space, with one field for the whole as-cast housing:**
- **Fixed:** only the machined interfaces (the seats' rings, the mounts' eyes) and the contract's kept-clear volumes. The design space is the packaging less those, the same in every iteration (D16).
- **Inside the run:**
  - the enclosure rule (new);
  - the two-part mould's casting filter (`topo_free.py --route cast`);
  - the least and greatest member;
  - every tilt and bed held with the factor of safety.
- **Drawn:** one smooth field (rho2sdf's two steps, the volume kept), exact only where machined.
- **Judged:**
  - FE, castability and watertightness;
  - the look, against `it1_free_5.5kg`;
  - each drawing's mass ratio to its field beside its stiffness ratio (Amroune's protocol).

**Later, if the look needs it:**
- a smoothness term inside the loop: Gauss curvature (note 04's idea, measured first on existing drawings) or the perimeter;
- a greatest member that varies with distance from the interfaces (the reviewer's adaptive rules made concrete).

**Not now:**
- a conforming level set (note 05: hours a run);
- neural fields (note 03: less stiff, wavy);
- any rebuild after the run (notes 01, 02, 04).
