# Housings in every style, fitted to the requirement: what neural CAD offers, and how the product uses it

**Date.** 9 October 2026, 19:45. **Asked by** the engineer, after the first housing in the trade's grammar (`grammar4`):

> "You have just shown me how you can create one housing. I gave you so many pictures. Can you create housings with all those pictures, and adapt them as per my requirements? Is it really possible? How? See bunnysocrazy.com … nothing is complete … but in the design phase, how can we use the best of these capabilities to create interesting, creative designs? … Tomorrow, if I send a picture of a Mercedes-Benz two-stage EV gearbox housing, will the agent adapt it and generate a new housing fitting my requirements? … I'm just trying to understand the potential of this product, how far it can go today."

The standard to meet is our own brief's G5, "Measurable creativity". Designs go beyond conventional patterns, and "new and better" is measured rather than claimed.

**What was read.**
- bunnysocrazy.com ("Awesome Neural CAD"), read through a page fetcher: its six sections and their entries, as the list describes them. The papers themselves were not read for this note.
- This repository's notes:
  - [CAD generation approaches](2026-10-05-cad-generation-and-bracket-datasets.md), with RealCADBench's measured rates for LLM CAD code;
  - [the AI-CAE landscape](2026-10-04-ai-cae-landscape.md);
  - [production housings against ours](2026-10-09-production-housings-against-ours.md).

## 1. In short

1. **Yes: in the design phase, housings in each of the reference pictures' styles, fitted to a given requirement, are possible today.** No single method does it, and no neural method alone gives a housing that fits its bearings, bolts and mounts, comes out of its mould and meets its stiffness lines. What does it is three things around our judges:
   - **a library of design languages**, the trade's grammar extended to many styles;
   - **reading**: a vision-language model turns a reference picture into a recipe in that language;
   - **an agent** that composes, adapts, builds, judges and compares many such recipes against the requirement.

   The neural methods in the list strengthen each part. None replaces the deterministic builder and judges, which keep every design real.
2. **One generator is one family; the product needs a vocabulary.** The generator becomes a builder of *recipes*: typed records of the choices a designer makes. These are:
   - the outline's family and the end walls' levels;
   - the cover's form;
   - which hard points the ribs join, and in which pattern;
   - the sections, and the features.

   Each reference picture is one style: a preset of choices. The agent's creativity is in combining and varying them, and in adding new feature types when a style needs one.
3. **A Mercedes picture** (or any other) becomes a recipe *of that style*, built on the user's own gear train and interfaces, then sized by the FE. It adapts the design language, not the exact geometry: the picture has no dimensions, and its insides are hidden. It is shown beside the other styles, each with its grade and the reason for its features.

## 2. What the field offers (Awesome Neural CAD's six sections)

| Section | What it does | Examples on the list | Its strength for us | Its limit for us | How we use it |
|---|---|---|---|---|---|
| **Generation** (~50) | New CAD models from nothing, a text or an image: B-rep diffusion and autoregression, LLM-made CAD | BrepGen, BrepDiff, AutoBrep, BrepGPT, ParaCAD; DeepCAD, SolidGen; FlexCAD, Text2CAD, FutureCAD, STEP-LLM; CADCrafter and CADDreamer (an image to CAD); GeoCAD (locally controllable) | Variety, and new shapes no template holds | Trained on small parts (the ABC and DeepCAD sets, mostly sketch-and-extrude). Nothing holds bearing seats on given axes, a bolt pattern, castability or stiffness | Ideas for local features (a rib family, a boss's form), always re-built and judged by our tools. LLM CAD code (below) is the near-term workhorse |
| **LLM CAD code** (within Generation) | A language model writes the CAD program | FlexCAD, Text2CAD, FutureCAD, STEP-LLM; CAD-Recode's CadQuery | New feature types written as code against our builder's API: a curved fan of ribs, a hexagonal lattice, a four-bolt bearing cap | RealCADBench (Sept 2026): 56-81 % of the programs run, solid IoU 0.28-0.54 | The agent extends the vocabulary. A new feature is kept only when its tests and the castability check pass |
| **Reconstruction** (~40) | CAD recovered from point clouds, images or drawings | CAD-Recode, Point2CAD, Img2CAD (a VLM factors the image), CAD2Program (2D drawings), Draw Step by Step, SECAD-Net | Reading a reference into structure | A photo of a complex casting gives at best a rough shape; the insides are invisible | **Reading a reference picture into a recipe** (its style), with the VLM's own vision; not into exact geometry |
| **Abstraction** (~15) | Shapes as programs and primitives; macros discovered across programs | ShapeAssembly, ShapeMOD (macro discovery), PrimitiveAnything, ShapeCraft (LLM agents building structured models) | Learning reusable moves from many designs | General shapes, not engineering | Later: learning the trade's moves from a library of good recipes (ShapeMOD's idea); ShapeCraft's agent pattern is ours |
| **Analysis** (~12) | Learning on B-reps: faces' kinds, fillets, questions about a model | UV-Net, BRepNet, DeFillet, CADTalk, QueryCAD | Fast encoders of a design; recognising features in an existing CAD | Need labelled data | A surrogate that ranks recipes before the FE (trained on our campaigns); labelling an existing housing's faces when one is given; defeaturing for FE |
| **Editing and retrieval** (~10) | Language-guided edits of an existing CAD; retrieval from images | B-repLer, CAD-Editor; ROCA, Scan2CAD | "Make the cover's ribs a lattice" on a given design | Edits generic geometry, not engineering intent | The agent edits recipes in words, and the tools rebuild and re-judge |
| **Datasets** (~8) | ABC, Fusion 360 Gallery, HistCAD, VideoCAD and others | | Training data | No gearbox housings in quantity | Our campaigns make the housing dataset: every recipe with its CAD, its grades and the reasons (the Data feature) |

**Why no one method is enough.** A housing's value lies in exact interfaces: seats on given axes, the motor's bolt circle, the vehicle's mounts. It must come out of its mould and meet stiffness lines. None of the generative methods holds these; our builder and judges do. The neural methods give the variety, the reading and the new features; the deterministic tools give the truth. That division is the product's thesis: agents choose, tools judge.

## 3. How it works: read, compose, extend, build, judge, learn, show

1. **The recipe.** The generator's choices become data, with a vocabulary of feature types:
   - the outline's family: a convex hull, lobes with blends, a round motor bell;
   - the end walls: flat, or stepped to each bearing;
   - the cover: a drum with a bridge, flat, or domed;
   - the rib graph: which hard points are joined, and the patterns (spokes, a wheel, triangles, a grid or lattice, crossed ribs, curved fans);
   - the sections (wall, ribs, bosses);
   - bearing caps, ears and ports.

   Each family in the 36 pictures is a **style preset**:

   | Preset | Its features |
   |---|---|
   | AVL | Triangulated cover; a wheel behind the motor face; ear-to-boss ribs |
   | Batom | A wheel motor face with an inner ring |
   | Kalyani | A curved fan of ribs round the big boss; a scalloped motor flange |
   | ZF | Crossed ribs over the gear's side wall |
   | Avtec and Magna | A rectangular grid on the walls |
   | Punch | Curved ribs sweeping across the end face |

2. **Read.** A vision-language model reads a reference picture into a recipe of the same vocabulary, with its confidence: the outline's family, the faces' patterns, the flange, the bosses, the ears. The dimensions are never taken from the picture: the contract fixes the gear train, the bearings, the split, the mounts and the motor's interface. A check tells us whether the reading is faithful: picture → recipe → our CAD → our picture, beside the reference.
3. **Compose.** The agent writes several deliberately different recipes. It draws on:
   - the requirement;
   - the engineer's guidance ("lightest", "quietest", "wheel motor face", "like this picture");
   - the references read;
   - what earlier campaigns learned.

   It anchors each style's patterns on this requirement's hard points: the spokes go to these bolts and the ears to these mounts.
4. **Extend.** When a style needs a feature the vocabulary lacks (a curved fan of ribs, say), the agent writes it as code against the builder's API: hard points, faces, rooms and the pull direction. The feature joins the vocabulary only when its tests pass, its parts come out of the mould and the FE still runs.
5. **Build.** The generator turns each recipe into the two halves' CAD, every face named, in seconds.
6. **Judge.** Every candidate is judged by the same deterministic tools:
   - castability on the CAD;
   - the FE: bearing displacement, misalignment against the shaft, modes against the orders, and the mass;
   - later, radiated noise and the motor's mass.
7. **Physics-led moves.** Topology optimisation in the voids round a design, with the pull direction and member sizes, says where material helps. The agent reads it into edges of the rib graph (Ivanov's practice), and a sizing sweep sets the sections.
8. **Learn.** Every recipe and its grade is a datapoint. The agent's priors improve, and a fast model ranks recipes before the FE runs (a B-rep encoder of the UV-Net kind, trained on our own campaigns). Recurring good moves become new macros (ShapeMOD's idea).
9. **Show.** A gallery of styles and architectures, each with its picture, its grade, its castability, its mass and its reasons, and the 3D viewer to look inside (PLT-9). The engineer picks, steers or asks for more.

## 4. The reference-picture scenario, step by step

Given a picture of a production two-stage EV reducer housing:
1. **The agent reads its design language:**
   - a lobed outline with a round motor bell;
   - a fan of curved ribs on the motor face, and a lattice on the cover's flat panels;
   - a scalloped flange of about 16 bolts;
   - three cast ears with gussets;
   - a bearing cap at the output.
2. **It writes that as a recipe on the user's contract.** The user's gear train sets the outline's circles and the depths. The user's mounts set the ears, and the user's motor sets the bell.
3. **It writes the features the vocabulary lacks** (the curved fan, say), tested as above.
4. **The tools build and judge it,** and the agent sizes it: the ribs' depth, the walls and the lattice's pitch.
5. **The result is shown beside the other styles,** each graded, with what each feature does for this requirement.

**What it is, and what it is not.**
- **It is:** a concept in that design language, fitted exactly to the user's interfaces and judged. Its rungs: simulation-feasible, and process-rule-feasible.
- **It is not a copy of the photographed part.** The picture has no dimensions, and its insides are guessed from the user's layout.
- **It is not production-ready.** Detailing, tolerances, casting simulation, durability and a test are still to come.
- **The principles, not the protected design.** A production housing's own design can be protected. The agent adapts its principles (wheel faces, fans, lattices) and says where each came from; it does not reproduce someone's part.

## 5. How far this goes today

| Now (weeks) | Months (research-grade) | Not yet |
|---|---|---|
| The recipe and its vocabulary; style presets from the 36 pictures; reading a picture into a recipe with the model's own vision; the agent composing, building and judging many recipes; LLM-written features admitted by tests; topology optimisation read into rib graphs; the gallery and the 3D viewer | A learned ranker from our own campaigns; macros discovered across good designs; neural B-rep generators for local feature ideas, re-built and judged; image-to-CAD of a complex casting as a rough starting point | A neural model that alone gives a castable, interface-exact, stiffness-proven housing; production readiness without engineering detailing and validation |

## 6. The PBIs it implies

- **LOP-12, the recipe and its style presets.** The generator's choices become a typed recipe, with presets for the six families (section 3.1), and a gallery of designs built from them on the EV reducer's contract, each judged.
- **LOP-13, a picture read into a recipe.** The VLM reads each of the 36 reference pictures into a recipe, and the round trip (picture → recipe → CAD → picture) shows the reading is faithful.
- **LOP-14, features written by the agent.** A feature API (hard points, faces, rooms, the pull) and a sandbox. A new feature type written as code is admitted by tests and the castability check.
- **PLT-9, the 3D viewer.** It sits on the Designs page: every part its own colour, with show/hide chips and opacity sliders.
- **Later:** the learned ranker, macro discovery, and neural local-feature ideas (the Learning feature).

## 7. Sources

1. Awesome Neural CAD ("The first curated list of Neural Computer-Aided Design (CAD) papers with visual previews"): https://bunnysocrazy.com/. Read through a page fetcher on 9 October 2026; its entries are cited as the list describes them.
2. This repository:
   - [CAD generation approaches and bracket datasets](2026-10-05-cad-generation-and-bracket-datasets.md), with RealCADBench's rates for LLM CAD code;
   - [the AI-CAE landscape](2026-10-04-ai-cae-landscape.md);
   - [production housings against ours](2026-10-09-production-housings-against-ours.md);
   - [the trade and art of housing design](2026-10-09-the-trade-and-art-of-housing-design.md);
   - [housing topology optimisation practice](2026-10-09-housing-topology-optimisation-practice.md).
3. Our own brief's goal G5, "Measurable creativity": [the research prompt](2026-10-05-perplexity-deep-research-prompt.md).
