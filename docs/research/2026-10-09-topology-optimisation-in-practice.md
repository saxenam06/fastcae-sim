# Topology optimisation in practice: iterations, interpretation, castings

Researched on 9 October 2026 (from 22:54) for LOP-16 (the housing from its interfaces, by topology optimisation on the misalignment), by a research subagent: check before citing.

**Status.** Complete at 23:30. Each claim is marked with how its source was read (see Sources); nothing marked *via search* or *metadata* should be cited publicly before the source is read.

**In short.**
1. **Iteration is the norm, but of a particular kind.**
   - **The standard sequence** since 1990 (Bremicker et al.; Olhoff et al.) and in OptiStruct's own framing: TO as the concept → a reading into CAD → FE → sizing and shape. Housing studies add a sizing round, typically of 10-20 variants.
   - **A second TO** in a changed or narrowed space is practised when the first run exposed a fault in the set-up (AVL, BMW, SEW).
   - **Shrinking the space automatically round the last result** did worse than one step in the one study that measured it (Rosnitschek et al. 2021: "trapped in local minima").
   - **Optimising thickness and rib layout together** beats doing them one after the other (Zhou et al. 2004; Tyflopoulos & Steinert 2020).
2. **Industry reads TO results by hand, helped by freeform fitting:** Inspire's PolyNURBS, Fusion's T-splines from a level set, nTop's smoothed implicits. Those give a smooth copy of the field, not ribs with parameters. The research answers are:
   - **skeleton-based feature reconstruction:** a casting variant exists (Mayer et al. 2023), and a vendor derives mid-planes by rule;
   - **explicit methods:** MMC, MMV, geometry projection, ribs laid out on thin-walled shells (Guo's group), and stiffener layout and height under a casting rule (H-DGTP).
3. **Casting rules inside the TO are standard:**
   - draw, single or split with a free parting surface;
   - least and largest member with a least gap;
   - symmetry and patterns.

   Without them the result cannot be read (Opel, AVL). Closed voids need their own check (the virtual temperature method). Hot spots are in no commercial TO.
   - **Our casting filter** is the split draw with a free parting surface, the right form for a housing half.
   - **The binding limit is resolution.** OptiStruct's rule of three elements per member means 6 mm voxels cannot draw a 6 mm rib. They draw plates, as LOP-16's runs did.
4. **Housing TO uses compliance first;** then seat displacements, mesh misalignment with the system model in the loop (Hexagon/GRM), local stiffness, modes and radiated power. Every reading is by hand into ribs, X-ribs, lattices or wheels, then sized. Two lessons for our objective:
   - **misalignment rewards balance, not stiffness** (Kawasaki's planet carrier);
   - **where the material goes matters more than how much** (a measured gearbox noise study).
5. **The celebrated shapes are not raw TO output.** The organic, lattice-like ones (GM's bracket, Airbus's partition, Porsche's e-drive housing) were printed. The castings (Opel's parts, Arup's nodes, a die-cast shock tower, BMW's mega-casting) are rib-and-wall designs read from TO and then sized. Their form came from people who chose, regularised (unity-in-variety: 11 of 12 TO designs rated more attractive after Gestalt grouping), blended (Mattheck's tensile triangles) and detailed.
6. **For LOP-16,** in order:
   - converge the whole-domain run (it is cycling), and use it as the map and the bound;
   - make the voxel model honest (the joint at the bolts; the skin's true thickness), and calibrate it once against the CAD;
   - read the field into the recipe, never into a freeform body;
   - build, check and prove at equal mass, then size;
   - a second, finer TO only where a measure still fails, with ribs as the variable: directional growth from the skin, or the rib graph by geometry projection.

**What is already settled elsewhere and not researched again.** The housing studies (Ivanov 2018, Jäger & Linde 2025, Kim 2024, Son 2019 and 2020, Amaral 2023, Triller 2023, Das 2011, Inoue 1992 and 1995, Ogata 2005, Klarin 2020, Barreiro 2019) are in [how housing topology optimisation is practised](2026-10-09-housing-topology-optimisation-practice.md); the Hexagon and GRM EDU deck and the agricultural gearbox's figures are in [the trade and art of housing design](2026-10-09-the-trade-and-art-of-housing-design.md). This report cites them and adds what they do not cover.

## 1. Is topology optimisation done iteratively?

**In short: yes, and it has been the textbook process since 1990, but "iterate" means three different things, and only one of them has evidence that it pays.**

**1.1 The three-phase process is the default, not a variant.**
- **Bremicker, Chirehdast, Kikuchi & Papalambros (1990, NASA/Air Force MDO symposium):** an optimal topology as a grey image (homogenisation), turned into a realisable design "using computer vision techniques", then "parameterized and treated in detail by sizing and shape optimization" (*abstract read*).
- **Olhoff, Bendsøe & Rasmussen (1991, CMAME 89:259-279):** the same chain, inside a CAD system: topology → boundary curves fitted → shape optimisation (*metadata read*).
- **Altair's OptiStruct documentation** names the two stages: *concept design* (topology, topography for beads in thin walls, free-size for thickness) and *design fine-tuning* (size, shape, free-shape) (*vendor pages, via search*).
- **Zhou, Pagaldipti, Thomas & Shyy (Altair, 2004, SMO 26:308-317)** say why the stages are usually separate: topology "is usually used as a tool for finding efficient design concepts at the early design stage, whereas sizing and shape optimization are tools for detailed design at a later stage" (*full text read*).
- **Bionics:** Mattheck's SKO (topology) and CAO (shape) methods are described in VDI 6224 Part 2 (2012), now withdrawn in favour of DIN ISO 18459:2016 (*catalogue entry read*; the standard itself is paid and not read). Opel's TopShape joined the two (§3.1).
- **Airbus UK (Krog, Tucker & Rollema, about 2002):** "Topology optimisation is performed to obtain a first view on an optimal configuration for the structure – an initial design with optimal load paths"; then the result was interpreted as trusses, with stiffeners added for out-of-plane stability, and sized and shaped against stress and buckling. 13 A380 droop-nose ribs were done in five weeks (*slides read through a page fetcher*). Altair's case study says over 500 kg saved per aircraft (*vendor claim, not checked*).

**1.2 What "iterate" means in practice: three loops.**

| Loop | What goes round | Names in the literature | Evidence that it helps |
|---|---|---|---|
| **A. Interpret → re-analyse → re-interpret** | The CAD reading, judged by FE, redrawn | "iterative design process" (Barreiro 2019, SEW); every housing study | Universal. Ivanov 2018 (AVL): the reading lost the TO's gain and was discarded; the cure was a better reading, not a better TO ([housing note](2026-10-09-housing-topology-optimisation-practice.md)) |
| **B. Re-run TO with a changed set-up** | The design space, the objective, the rules or the budget, set from what the last run showed | multi-stage, sequential or two-stage TO; "a second or third cycle" in narrowed spaces (Ivanov); weak-area sub-domains (Son 2020); free-size re-run after each rib added by hand (Triller 2023, BMW) | Mixed, see 1.3. Helps when the first run exposed a bad set-up (missing load case, wrong objective, missing rules) |
| **C. TO → size/shape of the interpreted design** | The parameters of the CAD reading | three-phase or integrated topology and shape optimisation; concept → fine-tuning | Consistent: the housing studies end with a sizing round, typically of 10-20 variants (Jäger & Linde's 13; Son's two studies; Honda's rib thickness) |

**1.3 Re-running TO: names and what the evidence says.**
- **Adaptive topology optimisation (Maute & Ramm, Struct. Optim. 10, 1995):** each design cycle's effective design space is adapted to the current material distribution and approximated by splines; this "decreases the number of design variables and leads to smooth results, moreover it can be directly joined to conventional shape optimization" (*abstract via search*). It is the formal version of "interpret, then re-optimise in a narrowed space".
- **Design space optimisation (Kim & Kwak, IJNME 53:1979-2002, 2002):** the design space itself is a variable, grown by a continuation through a "pivot" design space (*abstract via search*).
- **Multi-resolution and adaptive refinement (Gupta, van Keulen & Langelaar, IJNME 121:450-476, 2020):** each coarse cycle gives a good start for the next, finer one; speed-ups up to 10× (*abstract read*). This is "coarse run, then a finer run where the structure is", done automatically.
- **Progressive design-space reduction with casting simulation (Rosnitschek et al., Materials 14:3715, 2021; nTopology for TO and implicit geometry, Flow-3D for the casting):** the design space was shrunk step by step (step length 0.2, 90 % → 50 % volume, 4-6 iterations), with the casting simulation adding material back where the casting needed it. **The iterative variant did worse than the one-step variant:** manufacturability +68 % against +159 % for high-pressure die casting, +14 % against +29 % for low-pressure, and "the HPDC-IT approach is trapped in local minima for the chosen step-length of 0.2" (*full text read through a page fetcher*). Their description of industrial practice: "topology optimization is followed by a manual reconstruction of the design proposal and a process assurance simulation to endorse the design proposal. Consequently, this process is iteratively repeated."
- **Concurrent beats sequential, within limits (Zhou et al. 2004).** On their twist plate, topology and bead shape optimised together gave compliance 0.0069-0.0078, against 0.0122 for topology alone and 0.0131 for beads alone, at the same volume. But on the oil pan, adding sizing to contour and topology made the result worse, from local optima: "the resulting design should be assessed with a critical view" (*full text read*).
- **A benchmark of ten processes (Tyflopoulos & Steinert, Appl. Sci. 10:4496, 2020):** topology only, parametric only, the two in sequence, and the two together, on three benchmarks (30 runs). "Simultaneous Parametric and Topology Optimization" gave the lightest designs without loss of strength, at a longer run time (*abstract via search; MDPI refused the fetch*).
- **A non-design skin costs the ribs material (Zhou et al. 2004).** A base plate kept at 0.3 of the full thickness took about a third of the material; the topology hardly changed, but the compliance was 28 % higher, "owing to less material being available for forming ribs". This is our skin round the gears' room: its mass comes out of the ribs' budget, so its thickness is a design choice to test, not a given.

**1.4 What this means.** The evidence supports: a whole-domain run to find the load paths and the bound; a reading into parameterised CAD; FE on the CAD; a sizing and shape round on the reading's parameters; and a *second* TO only when the first exposed a set-up fault, or in a sub-space where a measure still fails. It does not support shrinking the design space round the last result in small automatic steps (Rosnitschek's local minima), nor treating a voxel run's claimed gain as the design's gain (Ivanov; fastcae's 1-of-5 polish, see the [housing note](2026-10-09-housing-topology-optimisation-practice.md) §1.7).

## 2. From a density field to a design

**In short: industry interprets by hand, helped by surface fitting; research reconstructs features from skeletons; and explicit methods skip the step by optimising members that are already CAD. None of the commercial routes gives a parametric rib-and-wall casting; the freeform routes give a smooth copy of the field.**

**2.1 Manual interpretation is still the standard.**
- **Every housing study read so far interprets by hand** ([housing note](2026-10-09-housing-topology-optimisation-practice.md) §1.3).
- **Opel (Harzheim & Graf, SMO 30:491-497, 2005, and SMO 31:388-399, 2006):** an optimisation process with integrated TO was "used very successfully at Adam Opel AG" on many cast components. But "the interpretation of design proposals is often very difficult" when the optimiser holds no manufacturing rules, in particular through "the tendency to create hollow proposals with a lot of holes" (*abstracts via search*).
- **Stangl & Wartzack (ICED 2015):** "the current standard method is a time consuming, long-winded manual reconstruction" (*abstract via search*).
- **Mayer, Denk & Wartzack (ICED 2023):** even with automated reconstruction, "the total amount of casting design guide lines, different casting techniques, as well as the interpretation of experienced engineers are not captured" (*full text read*).
- **What the interpreter does,** across these sources:
  - picks a density threshold, and re-analyses that iso-surface (Altair's Shape Explorer);
  - reads the members as a truss, or as plates and ribs, then adds what the optimiser left out: Airbus added stiffeners "for out-of-plane stability" to its truss-like ribs (Krog et al.);
  - imposes symmetry and regular patterns;
  - drops members that break a function (Ivanov's bridged oil port);
  - sets standard sections, drafts and fillets;
  - re-analyses the CAD, and sizes it.

**2.2 Freeform surface fitting: the commercial routes.**

| Tool | What it does with the field | What comes out | Casting support |
|---|---|---|---|
| **Altair Inspire** (OptiStruct inside) | Shape Explorer threshold; "Smooth Results"; **Fit PolyNURBS**, "a multistage process to automatically build PolyNURBS geometry on topology optimization results" (settings: number of faces, curvature, auto-creasing, and *Intersect* with the design space so that the non-design regions stay aligned); manual Shrinkwrap, Smooth and Fit tools for more control; Boolean, fillets, re-analysis | Subdivision-style PolyNURBS bodies, exportable to CAD | Draw directions in the TO (OptiStruct's, §3) (*docs read*) |
| **Autodesk Fusion generative design** | A level-set solver; the 0-iso-surface is extracted, T-spline surfaces are fitted to the organic part, and a watertight B-rep is composed with the preserved bodies (Autodesk patent US 11,886,165) | Many outcomes per solve, as editable T-spline and B-rep bodies; the user picks one (GM picked one of more than 150; VW narrowed about 200 to two, front and rear wheels) | A casting method: ejection direction (X, Y or Z, several giving several outcome sets), minimum draft, and a minimum thickness that outcomes may go below "in some cases … to meet other constraints" (*help pages read*) |
| **nTop** | *Implicit Body from Topology Optimization* (an iso-value of the density), *Smoothen Body* (a Gaussian blur, grid about the TO's element size), Booleans with the interfaces | An implicit (signed-distance) body, meshed or exported | None in the reading; Rosnitschek et al. (2021) coupled it to a casting simulation (§1.3): threshold 0.6, smoothed on a 1 mm grid, reconstruction in "less than 10 min" (*docs and paper read*) |

What all three give is a smooth copy of the field: organic surfaces with no rib parameters, no draft by construction (Fusion's casting method aside), and nothing a design rule can be applied to member by member.

**2.3 Feature-based reconstruction (research, and one vendor).**
- **Curve skeletons** suit beam-like results (Nana, Cuillière & François 2017; Amroune, Cuillière & François 2022: skeleton → sections → B-spline lofts → solid CAD). **Surface skeletons** (the medial axis) suit plate-like results: Mayer & Wartzack's line of work (2020-2023) turns the skeleton into an editable quad and T-spline skeleton, with each point's medial radius as its half-thickness ([housing note](2026-10-09-housing-topology-optimisation-practice.md) §2).
- **The casting variant (Mayer, Denk & Wartzack, ICED 2023, control arm):** members that would need cores or a complex mould split are turned 90° on the 2D skeleton. Their sections are graded by Heuver's circles to grow towards the feeder (directed solidification). The result is filled solid "so that no casting cores are needed".
  - **The mass moved with the reading.** TO target 25 % of the volume; the reading of a TO run with a demoulding constraint came out at 23 %, the casting-edited reading of an unconstrained run at **39 %**.
  - **Their comparison:** compliance × volume, 1,859 against 1,487 kJ·mm³. The edited reading was better per volume, but it was a different, much heavier design (*full text read*).
  - **The lesson for us:** readings must be compared at equal mass, or on a mass-normalised measure.
- **Rule-based mid-surfaces (Synera with RLE International):** mid-planes "directly derived" from TO results "following clearly defined rules". Claimed: 47 % less CAD effort and 84 % less time downstream, with "consistent quality in the topo interpretation" (*vendor case study read*). This is the thin-walled reading: walls and ribs as mid-surfaces with thicknesses, which is how castings are drawn.
- **Automatic geometry extraction followed by shape optimisation** (Swierstra, Gupta & Langelaar 2020, arXiv 2004.05448): a radial-basis level set fitted to the field, then shape-optimised with a finite-cell analysis. It gives smooth, accurate boundaries automatically, but not features (*abstract read*).
- **A review:** Subedi, Verma & Suresh (JCISE 20(6), 2020) class the post-processing methods. Their gap is the one above: the faceted output lacks "feature/parametric control" (*abstract via search*).

**2.4 Explicit and feature-mapping TO: members that are already CAD.**
- **Moving morphable components (MMC; Guo, Zhang & Zhong, J. Appl. Mech. 81:081009, 2014):** the design is a set of components (bars or plates with a position, angle, length and thickness) that "move, deform, overlap and merge". The variables are few, and the result is explicit geometry, so it goes to CAD without interpretation (*abstract via search*).
- **Moving morphable voids (Zhang et al., CMAME 322:590-614, 2017):** the dual, B-spline-bounded holes, in 3D (*metadata read*).
- **Geometry projection (Norato, Bell & Tortorelli, CMAME 293:306-327, 2015):** bars of fixed shape projected onto a density mesh, so the usual SIMP machinery and FE apply. Plates (Zhang, Norato, Gain & Lyu, SMO 54:1173-1190, 2016) and single-curvature plates (IJNME 114:128-146, 2017). A public MATLAB code (Smith & Norato, SMO 62:1579-1594, 2020) (*abstracts read*).
- **The family's review:** Wein, Dunning & Norato, "A review on feature-mapping methods for structural optimization", SMO 62:1597-1638 (2020).
- **Ribs on thin-walled shells, explicitly (Xu Guo's group, Dalian):**
  - computational conformal mapping lays rib components out on a curved shell (Jiang et al., CMAME 404:115745, 2023);
  - embedded solid MMCs (Huo et al., CMAME 417:116431, 2023).

  This is the closest published match to "ribs on a housing's skin as parameters" (*metadata read*).
- **Stiffener layout and height under a casting rule:**
  - H-DGTP (Liu, Li, Chen, Hu & Tong, SMO 52:903-913, 2015): a "Heaviside-function based directional growth topology parameterization (H-DGTP) of the casting constraints for simultaneously optimizing the layout and height of the stiffeners" on a base surface (*abstract read*);
  - variable-height stiffeners with an anisotropic casting filter (Zhou, Sun, Xu & Wang, SMO 65(11), 2022).

  These are a voxel TO restricted to ribs growing from the skin along the pull: our LOP-16 problem with the skin given.
- **What explicit methods cost** (*judgement, from the method papers' framing; not measured here*): they depend on the starting layout and the number of components, and are more prone to local optima. A density run first, to say where members want to be, followed by an explicit run seeded from it, uses each for what it is good at.

**2.5 Castings in particular.**
- **Designers turn the optimiser's bulk into a rib lattice:** GRM's EDU housing read "bulk reinforcement material" as "a cross-hatched lattice of ribs" ([trade and art](2026-10-09-the-trade-and-art-of-housing-design.md) §3.4). Porsche's printed e-drive housing kept "a continuous wall thickness of only 1.5 millimetres" and put the stiffness into honeycomb lattice structures (§4).
- **A thick blob on a wall is a request for bending stiffness there,** and ribs give it at a fraction of the mass. MAXDIM in OptiStruct exists for exactly this: it "reflects rib thickness control in casting" (§3).

## 3. Manufacturing constraints for castings

**In short: a draw rule, a least member, a largest member with a least gap, symmetry and patterns are standard in the commercial codes and well studied. Hot spots and feeding are not in any commercial TO; they are checked afterwards, or worked into the reading. The rules belong in the TO, because without them the result cannot be read (Opel, AVL). But each rule costs objective and convergence, so a relaxed run is kept beside the constrained one as the bound.**

**3.1 Why the rules go inside the optimisation.**
- **Opel's experience (Harzheim & Graf 2005, 2006):** proposals without manufacturing rules are hard to interpret: "hollow proposals with a lot of holes". Opel's answer was TopShape, a synthesis of shape optimisation (CAO) and topology optimisation (SKO) that takes the rules into account (*abstracts via search*).
- **AVL (Ivanov 2018):** without member limits and a pull direction, the solver thickened walls and made shapes that cannot be split-moulded ([housing note](2026-10-09-housing-topology-optimisation-practice.md)).
- **The cost (Mayer, Denk & Wartzack 2023):** "Adding constraints risks hindering the optimization and the quality of its result. Even a failure of the computation is possible." And "manufacturing design rules are rarely considerable all at once, why manual interpretation and editing often is necessary" (*full text read*).
- **fastcae measured the cost:** the casting rules inside its optimisation cost 11 % on displacement (plan §3).

**3.2 Draw (casting) constraints: the formulations.**

| Reference | Representation | How it works | Notes |
|---|---|---|---|
| **Gersborg & Andreasen**, SMO 44:875-881, 2011 | Density (SIMP) | An explicit parameterisation: the element densities along each casting line come from a Heaviside function of the design variables accumulated along the line. Density is therefore non-decreasing towards the parting plane, which rules out cavities and undercuts by construction | 123 citations (OpenAlex). Mechanism *from secondary descriptions* (a 2022 arXiv paper; Tosca's documentation), paper not read |
| **Liu, Li, Chen, Hu & Tong** (H-DGTP), SMO 52:903-913, 2015 | Density on a base surface | Stiffeners "grow" from a base surface in one direction; the Heaviside of the growth variable gives each stiffener's layout and height together; a base-surface mechanism controls the stiffeners' least length | *Abstract read*. The closest formulation to ribs growing from a housing's skin |
| **Vatanabe, Lippi, de Lima, Paulino & Silva**, Adv. Eng. Softw. 100:97-112, 2016 | Density, projection | One projection framework for least member, least hole, symmetry, pattern repetition, extrusion, turning, casting, forging and rolling | *Abstract via search* |
| **Allaire, Jouve & Michailidis**, in *Variational Analysis and Aerospace Engineering*, Springer, 2016 | Level set | A molding condition enforced by penalisation. It needs no feasible start yet converges to a castable shape, and it combines with least and largest thickness; 3D compliance examples | *Abstract via search* |
| **Li, Chen, Liu & Fan**, CAD 94:28-40, 2018 | Density + a virtual heat problem | The virtual temperature method: voids hold a virtual heat-generating material of high conductivity, solids a low one. An enclosed void heats up, so a limit on the highest temperature forbids enclosed voids and undercuts. Parting directions, one or several, are set by the heat-sink boundaries; no feasible start is needed | *Abstract via search*. It catches the closed voids that `castable.py` found in `box1_fl` |
| **Wang, Xu, Meng, Rong & Zhao**, Adv. Eng. Softw. 149:102886, 2020 | Density | Two models: a variable parting surface, optimised with the design, and a user-given one | *Abstract read* |
| **Wada, Yuge, Kizaki, Miura & Terada**, JSAE Trans. 53(1):138-144, 2022 | Density | Both-sided casting without a given separation plane: a relaxed one-sided rule on unstructured grids, with the separation surface placed at "the expected density ridge" by a p-norm centre of gravity along the casting axis | *Abstract read* |
| **Zhou, Sun, Xu & Wang**, SMO 65(11), 2022 | Density | Variable-height stiffeners with an anisotropic filter-based casting constraint | *Title and metadata only* |

**Our filter, placed in this family.**
- `topo_free.casting_filter` (ρ̃ = 1 − (1 − ρ)(1 − A·B)) fills the gap between metal above and metal below along each half's columns. Every column of a half is therefore one interval along its pull.
- That is a two-sided draw with the parting surface left free: OptiStruct's SPLIT, whose "splitting surface [is] optimized during optimization", and the models of Wang et al. 2020 and Wada et al. 2022.
- It is weaker than Gersborg & Andreasen's fixed-parting form, and that is correct for a housing half. A half is a cup: the end wall's columns end at the floor of the gears' room, the side walls' at the joint face. A rule that every column's metal must reach one fixed plane would fill the gears' room.
- It does not forbid an enclosed void that no column passes through. Li et al.'s virtual temperature is the check for that, as `castable.py` is on the CAD.

**3.3 How the commercial codes implement it.**
- **Altair OptiStruct** (DTPL card; help pages read):
  - **Draw:** `SINGLE` ("a single die will be used and it slides in the given drawing direction"; the bottom is the default contra part) or `SPLIT` ("two dies splitting apart in the given draw direction", the splitting surface optimised). `NOHOLE` forbids holes through the part along the draw: "the topology can only evolve gradually from the boundary one layer at a time". `STAMP` gives shell-like results. **Obstacles:** non-design regions must be declared "to preserve the casting feasibility". A draw constraint brings a default least member of three average element sizes.
  - **Least member (MINDIM):** "at least 3 times, and no greater than 12 times, the average element size"; outside that range it is reset. It works in two phases: "the first step converges to a solution with a large number of semi-dense elements. The second step tries to refine this solution to a solution with fully dense members."
  - **Largest member (MAXDIM),** which "reflects rib thickness control in casting":
    - at least 2 × MINDIM and at least 6 element sizes, and under half the thinnest width of the design region;
    - "the maximum reachable volume fraction is 0.5";
    - "use[d] sparingly until the technology becomes more robust … it might result in more intermediate density";
    - "it is strongly recommended that the behavior of the design problem be studied without MAXDIM first".
  - **Least gap (MINGAP):** only with MAXDIM, and greater than it.
  - **Extrusion.**
  - **Pattern repetition:** a main DTPL and secondaries, each with a local frame and scale factors; draw directions are carried over automatically.
  - **Pattern grouping:** one-, two- or three-plane symmetry, cyclic symmetry with N wedges, uniform density. It does not work with extrusion.
- **Dassault Abaqus Tosca** (demould control; documentation read):
  - The parameterisation filter (`FILTER_PARAM = YES`) groups "the elements in the demolding direction" and parameterises "the respective densities". It "ensures a castable design" whatever the objective.
  - **Parting options:** `MID_PLANE = STAMP`, `NONE`, `POINT` or `AUTO` (not `AUTO_TIGHT`, `SURFACE` or a non-zero `ANGLE`).
  - **Compatibility:** it works with member size and symmetry. Frozen elements are ignored by the option. It takes "the same or a slightly inferior number of optimization iterations".
  - **Caution:** stress objectives with non-stiffness constraints can leave intermediate densities.
- **Autodesk Fusion** (§2.2): ejection direction, least draft, least thickness, with outcomes that may break the least thickness "to meet other constraints".

**3.4 Member size: what the grid allows.**
- **Projection with a robust formulation** (eroded, intermediate and dilated designs) gives controlled least solid and void sizes (Wang, Lazarov & Sigmund, SMO 43:767-784, 2011). The review is Lazarov, Wang & Sigmund, "Length scale and manufacturability in density-based topology optimization", Arch. Appl. Mech. 86:189-218, 2016. The largest length scale: Lazarov & Wang, CMAME 318:826-844, 2017; Guest, SMO 37:463-473, 2009 (*metadata of the last not re-checked*).
- **Thin walls of one thickness** (Zhou, Nomura, Dede & Saitou, arXiv 1908.10825, 2019, Toyota Research Institute North America): least and largest feature size bounded together by Helmholtz PDE filters, with adaptive meshing so that the void costs little. The result is thin-walled geometry "with branches and holes", for "stamping, investment casting and composite manufacturing" (*abstract via search*).
- **The resolution rule matters for us.** OptiStruct's least member is three elements. On 6 mm voxels, the thinnest member the TO can draw honestly is about 18 mm; a 6 mm rib needs 2 mm voxels. A 6 mm field can say where ribs go and how much bending stiffness a face wants. It cannot draw a 6 mm rib: it draws a thick plate, the cover's end-face plate of LOP-16's first run.

**3.5 Process physics.**
- **Hot spots and feeding** are not in any commercial TO read here.
- **In research:** Heuver's circles are applied in the reading (Mayer et al. 2023); the casting simulation runs in the loop (Rosnitschek et al. 2021, Flow-3D, 30-180 minutes an iteration); enclosed voids are caught by a virtual heat problem (Li et al. 2018).
- **For printed sand moulds** the draw rule is a choice, not a law ([casting rules](2026-10-09-casting-rules-for-the-checker.md)). The thermal rules (Campbell's T-junction, a rib under half the wall) are not optional, and no TO holds them: they belong in the reading and in the checker.

## 4. Gearbox, EV reducer and e-axle housings

**In short:**
- **The objectives in use:** compliance first; then seat displacements, mesh misalignment with the drivetrain's model in the loop, local stiffness, eigenfrequencies, and radiated power or sound pressure.
- **Misalignment as the objective is rare but practised:** AVL through Ivanov; Hexagon with GRM; a Linköping thesis.
- **The design space** is the envelope less the gears' rooms; or bulk added outside a kept housing; or weak areas found by analysis.
- **The reading is always by hand,** into ribs along the seat-to-mount paths, X-ribs, lattices or wheels, and then sized.

**4.1 The studies.** The first block is from the [housing note](2026-10-09-housing-topology-optimisation-practice.md) and [the trade and art](2026-10-09-the-trade-and-art-of-housing-design.md), summarised; the second block is new here.

| Study | Housing | Objective | Design space | Into ribs and walls | Outcome |
|---|---|---|---|---|---|
| Ivanov 2018, KTH MSc for AVL | EV two-stage reducer, sand-cast Al | Compliance, then the six seat-centre displacements | Envelope less the gear cavity, then shell-conformal blocks with a pull per block | By hand in CATIA, a compromise of two runs | Discarded: deflected more than the original at its mass |
| Shahaj, Jamaluddin, Hughes (Hexagon) & Grubb (GRM), OED 2023 | Two-stage EDU, ratio 9.1, 160 N·m | Gear mesh misalignment, with Romax Enduro's system model updated "every n optimisation cycles"; mass; stress under yield | Not on the slides | Bulk "translated to a cross-hatched lattice of ribs"; radial ribs to the rim; mounts reinforced; 5 mm ribs | 13.5 → 7.6 kg at the baseline's lead correction |
| Jäger & Linde 2025, WEVJ 16:552 | Planetary EV, 150 kW | Least mass under torsional stiffness | Whole housing less the mounting faces; 8-fold cyclic symmetry | X-ribs; 13 sizing variants | −21 % mass, +5 % deformation |
| Kim et al. 2024, Sci. Rep. 14:4145 | UTV two-stage helical | Sound pressure at a microphone | Bulk added outside the kept housing; 3 domains | Ribs drawn "to consider the manufacturability and assembly" | −2.43 dB(A) at +0.2 % mass |
| Son et al. 2019, 2020, Appl. Sci. | Same | Local stiffness; radiated power | Weak areas found first | One rib family sized; or left unmanufacturable | +43 % local stiffness; −2.7 to −9.7 dB at +12 % mass |
| Ogata, Suzuki & Hiraoka 2005 (Honda), SAE 2005-01-1699 | Transmission housing | Rigidity | A double-layered mesh (skin kept, ribs grown) | Ribs "along bearing load transmission routes", then rib thickness by shape optimisation | Lighter at equal rigidity |
| Das 2011 (Honeywell), GT2011-46747 | Aero accessory gearbox | Seat misalignment and rotation against allowables | - | Ribs added and removed by hand | Judged at the seats |
| Amaral 2023, PhD, Centrale Lyon | Steel demonstrator | Compliance, with the bearing loads re-derived from the gearbox model each iteration | Less seats and joint | Holes closed; then modal sizing | −24 % mass, first mode halved |
| **Kandreegula, Sukumar, Endugu & Gupta 2015 (VE Commercial Vehicles)**, SAE 2015-01-0098 | Transmission housing, cast iron → aluminium | Non-linear TO in OptiStruct, to "achieve same existing/proven Cast Iron Housing stiffness for new Aluminium Housing" under the worst gear loads | An irregular design domain | Not in the abstract | "Experimentally verified" (*abstract read*) |
| **Liu L., Kang, Xi, Hu, Gong & Liu G. 2022 (NWPU)**, Chin. J. Mech. Eng. 35 | Single-stage herringbone gearbox | Radiated noise at the loudest field point | Chosen by contribution analysis: acoustic transfer vectors, modal and panel acoustic contributions; then TO to cut the normal velocity there | Four candidate structures added, then **measured** | "The noise reduction effect can be achieved only by adding the noise reduction structure to the gearbox center of the density nephogram" (*abstract read*) |
| **Qin & Jia 2018**, JAMDSM 12(1) | Shearer drum drive | Natural frequencies (OptiStruct), on a hybrid FE and lumped-parameter model of housing and gears | - | - | Less housing deformation and "equivalent mesh misalignment"; the effect on the mesh dynamics "is not very significant" (*abstract read*) |
| **Theling, Brimmers & Brecher 2021 (RWTH WZL)**, Forsch. Ingenieurwes. 85:543-551 | Planetary gearbox housing | Weighted: load distribution between the planets, excitation, mass, with tooth contact analysis in the loop | Shape ("form") optimisation of the housing and the ring gear | - | "Lightweight designs with superior dynamic performance" (*abstract read*) |
| **Kawasaki Heavy Industries 2018**, Kawasaki Technical Review 179 | Aero planetary gear carrier | Tilt of the planet axes | Stiffness of the front and back load paths | Re-proportioned plates | Tilt reduced and lighter; an endurance test's teardown found gears and bearings sound (*full text read*) |
| **Porsche 2020**, press release | Printed e-drive housing: motor and two-speed gearbox in one | Stiffness, mass, acoustics | "Design integration of components such as bearings, heat exchangers and oil supply", then "loads and interfaces", then "load paths", then "lattice structures" | A 1.5 mm continuous wall with honeycomb lattice structures | Housing −40 %, drive −10 %, stiffness between motor and gearbox +100 %; "the honeycomb structure reduces the oscillations of the thin housing walls" (*release read*) |
| **Lennström, Malm, Wurzinger & Cederlund 2026 (Volvo Cars, Xamera, Saab)**, SAE 2026-01-0687 | EDU housing ribs | Radiated sound power, squared velocity, radiation efficiency | Single ribs: length, thickness, curvature | - | A slight curvature of a rib's outer edge lowers the noise; some dimensions raise it, where the rib's own bending mode meets the peak of radiation efficiency (*abstract read*) |
| **Sharma, Hensel & Troge 2023 (Fraunhofer IWU)**, EURODYN 2023 | Simplified gearbox housing | Modes; radiated power under seat excitation | Panels | A hexagonal rib pattern | Not in the abstract |
| **Zhuang 2012**, Linköping thesis | Gearbox housing | Gear misalignment | - | - | *Title and a catalogue summary only; DiVA unreachable from here* |

**4.2 What the housing literature says about our objective.**
- **Misalignment is a difference, so balance beats stiffness.**
  - Kawasaki's planet-carrier result: the tilt came from "differences in stiffness between the front and back sides of the load-transfer path", and the cure was "a uniform stiffness both at the front and back sides", which was also lighter.
  - The same holds for a shaft whose two seats sit in different halves (our intermediate's tapered pair): what matters is that the two seats move alike, not that each moves little.
  - A misalignment objective can find that; a compliance objective cannot, because it rewards stiffness everywhere. This is the strongest argument for keeping LOP-16's objective, with compliance run once beside it for comparison (Ivanov's runs differed between the two).
- **The loads can follow the housing.** Hexagon/GRM update the system model every n cycles; Amaral re-derives the bearing loads each iteration; Son and Kim keep the drivetrain as a substructure.
  - For a shaft on two bearings the reactions are statically determinate and do not change with the housing.
  - The gears' mesh misalignment does, through the shafts' slopes. So the coupling matters once the gears' measure enters the grade ([trade and art](2026-10-09-the-trade-and-art-of-housing-design.md) §6), not before.
  - **When it does, FZG's method applies** (Schweigert, Weinberger, Otto & Stahl, Forsch. Ingenieurwes. 86:241-248, 2022). It brings the housing into the gear calculation as reduced stiffness matrices spread over each bearing bore's circumference rather than its centre point, checked against a hypoid test rig (*abstract read*). That agrees with the engineer's distributing coupling over the whole seat.
- **Where the material goes matters more than how much.** Liu et al. measured that only the structure at the density field's centre cut the noise. Son 2020 faults design areas chosen "based on experience or without clear criteria". Mao et al.'s shock tower (2017): "the choice of optimization space, which is critical and usually neglected".
- **Ribs radiate.** Volvo's 2026 rib study and the Chalmers and Volvo work in the [form rules](2026-10-09-housing-form-rules.md): a rib's own first bending mode near an order is a new noise source. Every reading is checked against the orders, not only the statics.

## 5. How the celebrated shapes are made

**In short: none of them is a raw optimiser output.** In each, the optimiser proposed load paths (or many outcomes), and people chose, regularised and detailed. The organic, lattice-like ones were printed. The castings are rib-and-wall designs informed by TO, and their form came from a designer.

**5.1 The examples and how each was made.**

| Part | Optimiser's share | People's share | Made by | Numbers | Source quality |
|---|---|---|---|---|---|
| **Airbus A380 droop-nose ribs** (Airbus UK with Altair, about 2002) | OptiStruct topology: "a first view on an optimal configuration … with optimal load paths" | Read as trusses, "regions with high density of material as structure and regions with low density of material as holes"; vertical stiffeners added for out-of-plane stability; T sections for one-sided machining, cruciform for two-sided; then sizing and shape against stress and buckling. "Care should be taken in the modelling of the load and boundary conditions" | Machined | 13 ribs in five weeks; over 500 kg per aircraft | Slides read; the 500 kg is Altair's claim |
| **GE jet-engine bracket challenge** (2013) | Entrants' own TO tools | Nearly 700 entries from 56 countries; ten were printed and tested to failure | Printed metal | The winner's often-quoted 84 % is *not on GE's page* | GE release read |
| **Airbus A320 "bionic partition"** (2015-16) | Generative design (The Living, an Autodesk studio), with growth rules from slime mould and bone | Airbus and APWorks: the cabin's requirements and the print | Printed Scalmalloy | 45 % (30 kg) lighter | Airbus newsroom read |
| **GM seat bracket** (May 2018) | Autodesk generative design: more than 150 outcomes | GM's engineers picked one; same hard points and space as the stamped part | Printed stainless steel; a proof of concept | 8 parts → 1; 40 % lighter, 20 % stronger | *Press, via several secondary sources*; GM's page unreachable |
| **VW Type 20 wheels** (2019) | Fusion generative design | About 200 designs narrowed to two, one per axle | Concept | 18 % lighter wheels | *Press, via search* |
| **Arup's tensegrity nodes** (2014-15) | OptiStruct for the material layout | Modelled in Rhino | Printed steel at first, then cast in 3D-printed sand moulds (3Dealise) | "Up to 75 per cent lighter" than welded nodes | *Press articles* |
| **Opel's cast parts** (Harzheim & Graf 2005-06) | TO, in many cast components | Interpretation, made hard by "hollow proposals with a lot of holes" until the rules entered the TO (TopShape) | Cast | Not in the abstracts | Abstracts |
| **Shock tower** (Mao, Fu, Lan & Zhao, ICADME 2017) | TO "to gain the distribution of stiffeners" | Size optimisation "to provide an optimal thickness for stiffeners"; design space chosen with care | Vacuum die-cast Al | −45 % against steel | Abstract read |
| **BMW mega-casting** (Triller et al. 2023) | TO and free-size, about 120 load cases | Best proposal picked by hand; ribs added by hand, free-size re-run after each; about 20 sizes | High-pressure die-cast | 25 kg less than a classical design | [Housing note](2026-10-09-housing-topology-optimisation-practice.md) |
| **Porsche e-drive housing** (2020) | Load paths, then lattice structures | Function integration first; a constant 1.5 mm wall | Printed Al | §4.1 | Release read |

**5.2 What the designer does after the optimiser.** These sources name six roles:
1. **Choose.** Among outcomes (GM over 150; VW about 200 to two) or among runs (Ivanov's compromise of two; Triller's load-case weightings). The choice is judgement, and it is where taste enters.
2. **Read the field as a structural system,** and add what the optimiser cannot see:
   - a truss plus stiffeners for buckling (Airbus);
   - a lattice where the field shows bulk (GRM);
   - a wheel of spokes behind a motor face (AVL's own housing);
   - ribs along the bearings' load routes (Honda).
3. **Regularise.**
   - **What it is:** symmetry, one rib family, an equal pitch, fair curves, every rib ending on a hard point.
   - **Loos, van der Wolk, de Graaf, Hekkert & Wu** (SMO 65(7), 2022) frame it as unity-in-variety. TO designs carry too much variety, and applying Gestalt grouping by hand made **11 of 12** of them rated more attractive (*abstract read*).
   - **Navez, Schmidt, Sigmund & Pedersen** (SMO 65:108, 2022) steer TO with a library of geometric patterns, so that the regularity is inside the optimisation (*metadata via search*).
   - This is the trade's grammar seen from the design side, and the engineer's "the end result must also look attractive".
4. **Blend the members into the bosses and walls.**
   - **Mattheck's method of tensile triangles** is a graphic rule, with no FE, for notch and junction shapes, taken from the buttress roots of trees (Mattheck, Kappel & Sauer, *Int. J. Design & Nature* 2(4):301-309, about 2007).
   - **His CAO and SKO** became VDI 6224 Part 2, now DIN ISO 18459.
   - **What it gives:** the fillet, and the rib's run-out into a boss, drawn by rule.
5. **Detail for the process:** sections, drafts, fillets, cores avoided, feeding (Heuver's circles, §2.3), and the casting simulation.
6. **Steer the optimiser.** Ha & Carstensen's human-informed TO (SMO, 2023) runs a short solution, lets the engineer change the least feature size where it matters, then re-solves "using the updated filtering map" (*abstract via search*). This is the seat the agent takes in our loop: judgement inside the optimisation, written as a reason, with the tool re-solving.

**5.3 For our product.** The engineer's 36 reference pictures are castings in the trade's grammar, not printed lattices ([production housings](2026-10-09-production-housings-against-ours.md)). The way to "amazing shapes" in that grammar is the cast examples' way:
- TO for the map: where the load paths run and which faces want stiffness;
- a designed silhouette and massing;
- a regular rib system read from the map;
- blended junctions;
- sizing by FE.

A freeform fit of the field would give the printed look, which the pictures do not ask for.

## 6. How long a run takes (added 10 October 15:04)

The engineer asked whether topology optimisation really takes the hour our runs take. It does not, at our size:
- **One GPU, tens of millions of elements, hours.** Träff, Rydahl, Karlsson, Sigmund and Aage (2023), simple GPU codes: 65.5 million elements in about 2 hours on a single GPU. A Tesla V100 study: 67.1 million elements, 150 iterations, in about 9.1 hours (about 220 s an iteration). Both solve the stiffness with a matrix-free multigrid-preconditioned CG on the GPU, not a direct factor.
- **Ours, LOP-18's first stage** (10 October, peak drive alone): 81,821 voxels (about 800 times smaller), 15-19 s an iteration. Of that, up to three assemblies and single-precision factors a step (GCMMA's inner loop, 2.2-2.4 s a factor), and 4.9-8.0 s in MMA's update, written in Python. The solves and adjoints take 0.6-0.9 s.
- **So the time is our implementation's:** MMA's update vectorised, one factor a step, the assembly on the GPU would give an estimated 3-4 s an iteration; a matrix-free multigrid solver, as the papers', about 1 s.

## What this means for our loop

**Where LOP-16 stands,** read from the logs in `data/first_loop/` at 23:22 (read only):
- **Run 1** (6 mm voxels, 100 iterations): 54 % of the metal grey.
- **Run 2** (6 mm, projection to β = 16, 240 iterations): grey down to 7-8 %. But from about iteration 217 the objective alternated every iteration between 0.159 and 0.196, with the change pinned at the 0.1 move limit and the worst seat swapping between the input's +z and −z seats. It did not converge; it cycled.
- **Run 2's reading:** the end faces thickened up to 78 mm deep on the cover and 108 mm on the motor side (about 30 mm on average where thickened), with 17 and 12 rib lines found.
- **Run 3** (5 mm, a 30 mm band, damping 0.3, a late move limit of 0.05): running, and still alternating at β = 4 (0.22 ↔ 0.35).

**The steps, in order, each with its evidence.**

1. **Treat the whole-domain run as the map and the bound, not as the design** (§1.4).
   - **Converge it first.** A two-cycle in which the worst seat swaps is the usual sign of an aggregated max under a fixed move limit. The standard cures are a bound formulation (minimise z, with every seat's ratio ≤ z) solved by MMA, and move limits that shrink as β grows (*standard practice; the references were not re-read here*). The test is that the objective stops alternating while the grey share stays low.
   - **Re-analyse the thresholded field.** Threshold the projected field at 0.5 (Rosnitschek used 0.6), apply the casting filter, and solve the 0/1 design in the same voxel model. The gap to the projected value is what the grey was credited with. Inspire's Shape Explorer re-analyses a chosen threshold for the same reason (§2.2).
   - **Run it relaxed and constrained,** with and without the casting filter, at 2-3 mass budgets. The relaxed curve of misalignment against mass is the bound (plan §3; [housing note](2026-10-09-housing-topology-optimisation-practice.md) §3, step 2).
2. **Make the voxel model honest where it flatters, before reading it.**
   - **The joint.** The voxel model glues the halves; the CAD joins them at the bolts through distributing couplings. Ivanov found that tied halves give "too high eigenvalues". Run 1 thickened the walls near the split, which may be the glue at work. Join the voxel halves only at the bolt bosses, as the CAD does.
   - **The skin.**
     - **How thick it is drawn:** one voxel layer, 6 mm in runs 1-2 and 5 mm in run 3, against the 4 mm least wall. Its mass comes out of the ribs' budget (Zhou et al. 2004: +28 % compliance when the base plate took a third of the material, §1.3). The frozen 3.71 kg (6 mm) and 3.24 kg (5 mm) include it.
     - **The options:** give the skin its 4 mm mass and stiffness, by a fixed intermediate density or a thickness-scaled element; or keep it, and say that the budget is penalised by the difference (*judgement*).
   - **Calibrate once.** Solve `lobed_e10s` and `grammar4` in the voxel model and compare with their CAD FE (fastcae measured voxels 1.0-2.4× stiffer). Use the voxels for ranking only.
3. **Read where and how much, not how thick** (§3.4). At three elements per member, 6 mm voxels draw nothing thinner than about 18 mm; the field puts a deep plate where a casting has ribs (run 2's 78-108 mm). From the field, read:
   - **per face,** the mass placed there and its depth (the reading's "columns thickened");
   - **the paths:** the surface skeleton of the field on the shell, between hard points (seats, bolt bosses, mounts, the motor's ring). Paths that recur across runs, budgets and resolutions are robust, as Ivanov's rib "suggested in every simulation" was;
   - **the massing:** a deep plate over two bearings asks for a bridge or a drum. Deep thickening on a face asks for bending stiffness there, which the trade gives with deep ribs or a lattice (GRM's lattice, Porsche's honeycomb, §2.5).
4. **Write the reading into the recipe, never into a freeform body.**
   - **[tool]** The reading proposes recipe choices: outline, levels, cover form, the rib graph's edges, and the heights per face.
   - **[agent]** The agent decides which to take, with a reason for each (choose, read, regularise: §5.2).
   - **Why not freeform:** fitting PolyNURBS, T-splines or a smoothed SDF (§2.2) would copy the field, skip the grammar and the casting checks, and give the printed look (§5.3). The `_smooth.stl` is a picture of the map, not a candidate.
5. **Build, check and prove at equal mass.**
   - LOP-15's clean-rib rules, `castable.py`, then FE on the CAD.
   - Compare each reading with the baseline and with the other readings at equal mass, or on a mass-normalised measure. One target of 25 % gave readings at 23 % and 39 % (Mayer et al. 2023, §2.3).
6. **Size the recipe's parameters:** 6-9 proofs over rib heights, thicknesses, pitches and the end walls' thickness. This is the fine-tuning stage (§1.1; Jäger & Linde's 13 variants; Mao et al.'s shock tower).
7. **A second TO only for a measure that still fails, in a sub-space, finer, with ribs as the variable** (§1.3, §2.4, §3.2).
   - **Where:** the face where the failing seat's sensitivity per kilogram is highest (Son 2020; Liu et al.'s density centre, §4.1).
   - **What is frozen:** the CAD reading, as Kim kept the housing and added bulk, and as Honda grew ribs from a kept skin.
   - **Density form:**
     - ribs grow from the skin along the pull (H-DGTP; Zhou et al. 2022's anisotropic casting filter), at 2-3 mm voxels inside the sub-space;
     - a largest-member rule, so that it draws ribs and not plates. OptiStruct's MAXDIM "reflects rib thickness control in casting", and needs at least six elements.
   - **Explicit form, the better fit for a recipe generator:** optimise the rib graph's own parameters on the voxel model by geometry projection: the position, height and thickness of each rib between hard points (Norato's bars and plates; Guo's ribs on thin-walled shells). The result is CAD-ready ribs that obey the grammar by construction. Seed it from the density map, against its local optima.
   - **Not this:** shrinking the design space automatically in small steps; Rosnitschek's iterative variant was "trapped in local minima" (§1.3).
8. **Keep the misalignment objective, and run compliance once beside it** (§4.2).
   - Misalignment rewards balance (Kawasaki), which compliance cannot see.
   - **What to look for in the field:** whether the intermediate's two seats, in different halves, are driven to move alike rather than each to move little.
9. **Casting inside the TO.**
   - **Keep the filter:** a free parting surface per half (§3.2).
   - **Add a closed-void check on the thresholded field,** a flood fill from the mould's side, as `castable.py` does on the CAD. Move Li et al.'s virtual temperature into the TO only if closed voids recur.
   - **The thermal rules** stay in the reading and the checker (§3.5).
10. **Stop by the rule already written** ([housing note](2026-10-09-housing-topology-optimisation-practice.md) §3, step 8):
    - pass with margin;
    - the relaxed bound misses the goal;
    - two readings in a row fail;
    - or the budget of proofs is spent.

**Where this goes beyond practice.** In every study read, the steps between the field and the proven CAD were manual and done once or twice. The loop can do them many times overnight, and keep the reason and the result of each as data:
- several runs (budgets, objectives, relaxed and constrained, two resolutions);
- several readings per run, each a recipe with its hypothesis;
- every reading built, checked and judged by FE at equal mass.

Two things in it come from no single source:
- reading a TO field into a design grammar's recipe;
- comparing the readings at equal mass against the TO's own bound.

## Sources

**How each was read:**
- *full text* or *docs read*: read through a page fetcher or extracted from the PDF;
- *abstract read*: the publisher's or an index's abstract was read;
- *via search*: seen only through search summaries (low confidence);
- *metadata*: the bibliographic record only.

Bibliographic records were checked against OpenAlex where marked. Paid standards and paywalled papers were not read.

**1. Iteration and the design process**
1. Bremicker, Chirehdast, Kikuchi & Papalambros, *Integrated topology and shape optimization in structural design*, Third Air Force/NASA Symposium on Recent Advances in MDO, 1990: https://ntrs.nasa.gov/citations/19940004700. The three-phase process: topology → computer-vision reading → sizing and shape (*abstract read*). Its journal version (Mech. Struct. Mach. 19, 1991) was not checked.
2. Olhoff, Bendsøe & Rasmussen, *On CAD-integrated structural topology and design optimization*, CMAME 89:259-279, 1991, doi:10.1016/0045-7825(91)90044-7. Topology → fitted boundaries → shape optimisation in CAD (*metadata*).
3. Zhou, Pagaldipti, Thomas & Shyy (Altair), *An integrated approach to topology, sizing, and shape optimization*, SMO 26:308-317, 2004, doi:10.1007/s00158-003-0351-2; copy at https://giref.ulaval.ca/~deteix/bois/documents_references/zhou.pdf. Why the stages are separate; concurrent topology and contour beat either alone; a base plate costs the ribs material (*full text*).
4. Altair, OptiStruct applications (concept: topology, topography, free-size; fine-tuning: size, shape, free-shape): https://altair.com/optistruct-applications (*via search*).
5. Krog, Tucker & Rollema (Airbus UK), *Application of topology, sizing and shape optimization methods to optimal design of aircraft components*: https://www.slideshare.net/slideshow/airbus-topology-optimization-methods-for-optimal-aircraft-components/8693047. Topology → truss reading with stiffeners → sizing and shape; the A380 droop-nose ribs (*slides read through a fetcher*).
6. Maute & Ramm, *Adaptive topology optimization*, Structural Optimization 10, 1995, doi:10.1007/BF01278493. Each cycle's design space adapted to the material and spline-approximated, then shape optimisation (*abstract via search*).
7. Kim & Kwak, *Design space optimization using a numerical design continuation method*, IJNME 53(8):1979-2002, 2002. The design space as a variable (*abstract via search*).
8. Gupta, van Keulen & Langelaar, *Design and analysis adaptivity in multiresolution topology optimization*, IJNME 121(3):450-476, 2020, doi:10.1002/nme.6217; arXiv:1811.09821. Coarse-to-fine adaptivity, up to 10× faster (*abstract read*).
9. Rosnitschek et al., *Combining structural optimization and process assurance in implicit modelling for casting parts*, Materials 14(13):3715, 2021: https://pmc.ncbi.nlm.nih.gov/articles/PMC8269844/. nTopology plus Flow-3D; one-step against iterative design-space reduction; the iterative variant was trapped in local minima (*full text through a fetcher*).
10. Tyflopoulos & Steinert, *Topology and parametric optimization-based design processes for lightweight structures*, Appl. Sci. 10(13):4496, 2020, doi:10.3390/app10134496. Ten processes on three benchmarks; simultaneous was lightest (*abstract via search*).
11. VDI 6224 Blatt 2:2012 (withdrawn), replaced by DIN ISO 18459:2016, *Biomimetic structural optimization*: https://www.dinmedia.de/en/technical-rule/vdi-6224-blatt-2/150087897 (*catalogue entry*; the standards are paid and were not read).

**2. Interpretation and explicit methods**

12. Harzheim & Graf (Adam Opel AG), *A review of optimization of cast parts using topology optimization*: Part I, SMO 30(6):491-497, 2005, doi:10.1007/s00158-005-0553-x; Part II (with manufacturing constraints), SMO 31:388-399, 2006 (DOI not checked). Opel's practice; proposals hard to read without rules; TopShape (*abstracts via search*).
13. Stangl & Wartzack, *Feature based interpretation and reconstruction of structural topology optimization results*, ICED 2015: https://www.designsociety.org/publication/37838/ (*abstract via search*).
14. Mayer, Denk & Wartzack, *Reconstruction of topology optimized geometry with casting constraints in a feature-based approach*, ICED 2023, doi:10.1017/pds.2023.302. A medial-axis reading with Heuver's circles; readings at 23 % and 39 % of the volume against a 25 % target (*full text*).
15. Altair Inspire, *Fit PolyNURBS to the generated shape*: https://help.altair.com/inspire/en_us/topics/inspire/structure/fit_polynurbs_c.htm; tutorial *Generating CAD from optimization results*: https://help.altair.com/inspire/en_us/topics/inspire/tutorials/tut_analyzingshape_c.htm (*docs read*).
16. Autodesk Fusion generative design, *Casting parameters*: https://help.autodesk.com/cloudhelp/ENU/Fusion-GenerativeDesign/files/GD-CASTING-REF.htm (*docs read*). Autodesk patent US 11,886,165, level set → T-splines → watertight B-rep: https://patents.justia.com/patent/11886165 (*via search*).
17. nTop documentation, *Post-processing* (Implicit Body from Topology Optimization, Smoothen Body): https://docs.ntop.com/lessons/intro-to-topology-optimization/post-processing (*via search*).
18. Synera with RLE International, *Topology result interpretation*: https://www.synera.ai/focused-case-study/topology-result-interpretation. Rule-based mid-planes; −47 % CAD effort (*vendor page read*).
19. Swierstra, Gupta & Langelaar, *Automated and accurate geometry extraction and shape optimization of 3D topology optimization results*, arXiv:2004.05448, 2020 (*abstract read*).
20. Subedi, Verma & Suresh, *A review of methods for the geometric post-processing of topology optimized models*, JCISE 20(6), 2020: https://ersl.me.wisc.edu/?p=324 (*abstract via search*).
21. Guo, Zhang & Zhong, *Doing topology optimization explicitly and geometrically: a new moving morphable components based framework*, J. Appl. Mech. 81(8):081009, 2014, doi:10.1115/1.4027609 (*metadata; method via search*).
22. Zhang et al., *Explicit three dimensional topology optimization via Moving Morphable Void (MMV) approach*, CMAME 322:590-614, 2017, doi:10.1016/j.cma.2017.05.002 (*metadata*).
23. Norato, Bell & Tortorelli, *A geometry projection method for continuum-based topology optimization with discrete elements*, CMAME 293:306-327, 2015, doi:10.1016/j.cma.2015.05.005 (*metadata*).
24. Zhang, Norato, Gain & Lyu, *A geometry projection method for the topology optimization of plate structures*, SMO 54(5):1173-1190, 2016, doi:10.1007/s00158-016-1466-6. Zhang, Gain & Norato, curved plates with placement bounds, IJNME 114(2):128-146, doi:10.1002/nme.5737 (*abstracts read*).
25. Smith & Norato, *A MATLAB code for topology optimization using the geometry projection method*, SMO 62(3):1579-1594, 2020, doi:10.1007/s00158-020-02552-0 (*abstract read*).
26. Wein, Dunning & Norato, *A review on feature-mapping methods for structural optimization*, SMO 62(4):1597-1638, 2020, doi:10.1007/s00158-020-02649-6 (*metadata*).
27. Jiang, Huo, Liu, Du, Zhang, Li & Guo, *Explicit layout optimization of complex rib-reinforced thin-walled structures via computational conformal mapping (CCM)*, CMAME 404:115745, 2023, doi:10.1016/j.cma.2022.115745 (*metadata*).
28. Huo, Liu, Liu, Du, Zhang & Guo, *A novel explicit design method for complex thin-walled structures based on embedded solid moving morphable components*, CMAME 417:116431, 2023, doi:10.1016/j.cma.2023.116431 (*metadata*).
29. Nana, Cuillière & François 2017, and Amroune, Cuillière & François, CAD 145:103183, 2022: curve-skeleton reconstruction ([housing note](2026-10-09-housing-topology-optimisation-practice.md) sources 18-22).

**3. Manufacturing constraints**

30. Gersborg & Andreasen, *An explicit parameterization for casting constraints in gradient driven topology optimization*, SMO 44(6):875-881, 2011, doi:10.1007/s00158-011-0632-0 (*metadata; mechanism from secondary descriptions*).
31. Liu, Li, Chen, Hu & Tong, *H-DGTP: a Heaviside-function based directional growth topology parameterization for design optimization of stiffener layout and height of thin-walled structures*, SMO 52(5):903-913, 2015, doi:10.1007/s00158-015-1281-5 (*abstract read*).
32. Vatanabe, Lippi, de Lima, Paulino & Silva, *Topology optimization with manufacturing constraints: a unified projection-based approach*, Adv. Eng. Softw. 100:97-112, 2016, doi:10.1016/j.advengsoft.2016.07.002 (*abstract via search*).
33. Allaire, Jouve & Michailidis, *Molding direction constraints in structural optimization via a level-set method*, in *Variational Analysis and Aerospace Engineering*, Springer Optimization and Its Applications 116, 2016; HAL hal-01242945 (*abstract via search*; HAL refused the fetch).
34. Li, Chen, Liu & Fan, *Topology optimization design of cast parts based on virtual temperature method*, CAD 94:28-40, 2018, doi:10.1016/j.cad.2017.08.002 (*abstract via search*).
35. Wang, Xu, Meng, Rong & Zhao, *Topology optimization of cast parts considering parting surface position*, Adv. Eng. Softw. 149:102886, 2020 (*abstract read*).
36. Wada, Yuge, Kizaki, Miura & Terada, *Topology optimization under both-sided casting constraint without specifying the separation plane*, JSAE Trans. 53(1):138-144, 2022: https://tech.jsae.or.jp/paperinfo/en/content/jt202201.23/ (*abstract read*).
37. Zhou, Sun, Xu & Wang, *Variable-height stiffener design using topology optimization with anisotropic filter-based casting constraints*, SMO 65(11), 2022, doi:10.1007/s00158-022-03428-1 (*metadata*).
38. Altair OptiStruct, *Topology optimization manufacturability* (MINDIM, MAXDIM, MINGAP, draw, extrusion, pattern repetition and grouping): https://help.altair.com/hwsolvers/os/topics/solvers/os/mfg_topology_opt_intro_c.htm (*docs read*).
39. Abaqus (Tosca), *Demold constraints with parameterization filter*: https://docs.software.vt.edu/abaqusv2025/English/TsoUserMap/tso-c-user-TopOpt-DesArea-ManuFilter.htm (*docs read*).
40. Zhou, Fleury, Shyy, Thomas & Brennan, *Progress in topology optimization with manufacturing constraints*, 9th AIAA/ISSMO MAO Symposium, 2002. The paper behind OptiStruct's rules (*citation only*).
41. Wang, Lazarov & Sigmund, *On projection methods, convergence and robust formulations in topology optimization*, SMO 43(6):767-784, 2011, doi:10.1007/s00158-010-0602-y (*metadata*).
42. Lazarov, Wang & Sigmund, *Length scale and manufacturability in density-based topology optimization*, Arch. Appl. Mech. 86:189-218, 2016, doi:10.1007/s00419-015-1106-4; Lazarov & Wang, *Maximum length scale in density based topology optimization*, CMAME 318:826-844, 2017, doi:10.1016/j.cma.2017.02.018 (*metadata*). Guest, *Imposing maximum length scale in topology optimization*, SMO 37:463-473, 2009 (*not re-checked*).
43. Zhou, Nomura, Dede & Saitou, *Topology optimization for 3D thin-walled structures with adaptive meshing*, arXiv:1908.10825, 2019 (*abstract via search*).

**4. Gearbox and e-drive housings** (studies 1-11 of the [housing note](2026-10-09-housing-topology-optimisation-practice.md) and the Hexagon/GRM deck of [the trade and art](2026-10-09-the-trade-and-art-of-housing-design.md) are not repeated here)

44. Kandreegula, Sukumar, Endugu & Gupta (VE Commercial Vehicles), *Structural non-linear topology optimization of transmission housing and its experimental verification*, SAE 2015-01-0098: https://saemobilus.sae.org/content/2015-01-0098 (*abstract read*).
45. Liu L., Kang, Xi, Hu, Gong & Liu G., *Optimal design and experimental verification of low radiation noise of gearbox*, Chin. J. Mech. Eng. 35, 2022, doi:10.1186/s10033-022-00801-5 (*abstract read*).
46. Qin & Jia, *Hybrid dynamic modeling of shearer's drum driving system and the influence of housing topological optimization on the dynamic characteristics of gears*, JAMDSM 12(1), 2018, doi:10.1299/jamdsm.2018jamdsm0020 (*abstract read*).
47. Theling, Brimmers & Brecher, *Reducing mass while improving the operational behavior: form optimization of planetary gearbox housings*, Forsch. Ingenieurwes. 85:543-551, 2021, doi:10.1007/s10010-021-00445-2 (*abstract read*).
48. Schweigert, Weinberger, Otto & Stahl, *Advanced method of including housing stiffness into calculation of gear systems*, Forsch. Ingenieurwes. 86:241-248, 2022, doi:10.1007/s10010-022-00585-z (*abstract read*).
49. Kawasaki Heavy Industries, *Advancement of aircraft gear box design technology*, Kawasaki Technical Review 179, October 2018: https://global.kawasaki.com/en/corp/rd/magazine/179/pdf/n179en09.pdf. Stiffness balance against planet-axis tilt (*full text*).
50. Porsche, *Prototype for small-series production: electric drive housing from a 3D printer*, 18 December 2020: https://newsroom.porsche.com/en_US/technology/porsche-protoype-small-production-electric-drive-housing-3d-printer-23277.html (*release read*).
51. Lennström, Malm, Wurzinger & Cederlund (Volvo Cars, Xamera, Saab), *Rib design of electric drive unit housings for reduced noise radiation*, SAE 2026-01-0687: https://saemobilus.sae.org/papers/rib-design-electric-drive-unit-housings-reduced-noise-radiation-2026-01-0687 (*abstract read*).
52. Sharma, Hensel & Troge (Fraunhofer IWU), *Effect of a hexagonal rib pattern on the dynamic response of a gearbox housing*, EURODYN 2023: https://eurodyn2023.dryfta.com/program/abstract-archive/abstract/public/588/effect-of-a-hexagonal-rib-pattern-on-the-dynamic-response-of-a-gearbox-housing (*abstract read*).
53. Zhuang, *Gearbox housing topology optimization with respect to gear misalignment*, Linköping University, 2012, urn:nbn:se:liu:diva-87263 (*not read*: DiVA refuses connections from here; a lead worth reading, since it is our objective).
54. Mao, Fu, Lan & Zhao, *Lightweight design of a shock tower based on topology and size optimization*, ICADME 2017: https://www.atlantis-press.com/proceedings/icadme-17/25878273 (*abstract read*).

**5. Celebrated parts and the designer's role**

55. Airbus, *Pioneering bionic 3D printing* (the A320 partition), March 2016: https://www.airbus.com/en/newsroom/news/2016-03-pioneering-bionic-3d-printing (*read*).
56. GE, *GE announces winners of 3D printing design quest*, 11 December 2013: https://www.ge.com/news/press-releases/ge-announces-winners-3d-printing-design-quest (*read*).
57. GM and Autodesk seat bracket, May 2018. GM's release (https://app.3blmedia.com/news/advanced-software-design-technology-leads-gm-lighter-more-efficient-vehicles) was unreachable; numbers from secondary reports, e.g. https://www.compositesworld.com/news/gm-seat-bracket-made-with-autodesk-generative-design-software (*via search*).
58. Volkswagen and Autodesk, Type 20 concept, July 2019: https://techcrunch.com/2019/07/08/volkswagen-and-autodesk-turned-a-vintage-microbus-into-a-tech-design-showcase/ (*via search*).
59. Arup, nodes cast in 3D-printed sand moulds: https://www.azuremagazine.com/article/arup-3d-printing-sand-moulds/ (*press article read*). Galjaard, Hofman, Perry & Ren, *Optimizing structural building elements in metal by using additive manufacturing*, IASS 2015 (*title only*).
60. Loos, van der Wolk, de Graaf, Hekkert & Wu, *Towards intentional aesthetics within topology optimization by applying the principle of unity-in-variety*, SMO 65(7), 2022: https://research.tudelft.nl/en/publications/towards-intentional-aesthetics-within-topology-optimization-by-ap (*abstract read*).
61. Navez, Schmidt, Sigmund & Pedersen, *Topology optimization guided by a geometrical pattern library*, SMO 65:108, 2022 (*via search*).
62. Mattheck, Kappel & Sauer, *Shape optimization the easy way: the "method of tensile triangles"*, Int. J. Design & Nature 2(4):301-309, about 2007 (the year is inferred from the volume): https://www.iieta.org/journals/ijdne/paper/10.2495/D%26N-V2-N4-301-309 (*abstract read*).
63. Ha & Carstensen, *Human-informed topology optimization: interactive application of feature size controls*, SMO, 2023: https://dspace.mit.edu/handle/1721.1/148295 (*via search*).

**This repository's notes used:**
- [how housing topology optimisation is practised](2026-10-09-housing-topology-optimisation-practice.md);
- [the trade and art of housing design](2026-10-09-the-trade-and-art-of-housing-design.md);
- [production housings against ours](2026-10-09-production-housings-against-ours.md);
- [casting rules for the checker](2026-10-09-casting-rules-for-the-checker.md);
- [housing form rules](2026-10-09-housing-form-rules.md);
- the [plan](../features/product/plan.md) §3;
- LOP-16's logs in `data/first_loop/` (`topofree_run1-3.log`, `*_projected_read.json`), read only.
- Section 6 (run times): Träff, Rydahl, Karlsson, Sigmund and Aage, "Simple and efficient GPU accelerated topology optimisation: codes and applications", 2023 (https://hgpu.org/?p=28174); "GPU accelerated large-scale topology optimization of 3D continuum structures" (https://research.buaa.edu.cn/en/publications/gpu-accelerated-large-scale-topology-optimization-of-3d-continuou/), read from their abstracts by web search; LOP-18's log `data/first_loop/chain_contract_drive_s1.log`.
