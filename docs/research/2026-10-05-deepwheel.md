# DeepWheel, and wheels as a part family

*5 October 2026. Paper facts were read from the arXiv HTML version in the main session. The assessment is ours.*

## The paper

**DeepWheel: Generating a 3D Synthetic Wheel Dataset for Design and Performance Evaluation.**
Soyoung Yoo and Namwoo Kang (KAIST / Narnia Labs, the group behind DeepJEB). arXiv 2504.11347, April 2025.
[arXiv](https://arxiv.org/abs/2504.11347) · [HTML](https://arxiv.org/html/2504.11347)

| | |
|---|---|
| Pipeline | Stable Diffusion v1.4 images (mask-conditioned) → fine-tuned Marigold depth estimation → depth map → point cloud → marching cubes mesh → STEP. Topology optimisation (compliance + similarity to a reference, 4/5/6-fold rotational symmetry) adds variants |
| Counts | 6,249 rendered images and depth maps; 904 simulated 3D designs (out of 1,000 sampled by Latin hypercube over a ViT/t-SNE embedding) |
| Fixed geometry | Rim and hub are fixed (19 × 8.5 in, offset 45 mm, PCD 114.3 mm, bore 66 mm). Only the spoke region varies |
| Physics | **Free-free modal analysis only.** 15 modes; mode 7 (rim) and mode 11 (spoke) plus mass give a performance score. No static, fatigue or impact cases |
| Solver | Altair SimLab / OptiStruct, Tet10, average element size 6 mm |
| Material | A356-T6 cast aluminium |
| Formats | PNG images, depth maps, STL, STEP (converted from meshes, not parametric), CSV |
| Licence | **CC BY-NC 4.0** (non-commercial). Hosted on Google Drive via smartdesignlab.org/datasets |
| Results reported | Dataset diversity metrics. **No surrogate-model results** |

**The same lab's earlier wheel work:**
- [Oh et al. 2019, *Deep generative design*](https://pure.kaist.ac.kr/en/publications/deep-generative-design-integration-of-topology-optimization-and-g/),
  J. Mech. Des. 141(11): topology optimisation plus GANs, 2D wheels.
- Yoo et al. 2021, *Integrating deep learning into CAD/CAE system: generative design and evaluation of 3D conceptual
  wheel*, Struct. Multidisc. Optim. 64(4):2725–2747.

Wheels are an established benchmark in generative-design research.

## Can we use their generator, or their data, to train one?

*Checked 5 October 2026.*

**Availability.**
- **Released:** only the **dataset** (Google Drive, via smartdesignlab.org/datasets).
- **Not found:** generator code or the fine-tuned depth-model weights.
- **The parts are public:**
  - Stable Diffusion v1.4 (CreativeML OpenRAIL-M);
  - [Marigold](https://github.com/prs-eth/Marigold), whose code is Apache-2.0. The licence of the weights still
    needs checking.

**Limits of their generator.**
- **It is 2.5D.** Geometry comes from one front-view depth map, so the result is a height field. It cannot
  represent back-side lightening pockets, undercuts or hidden windows.
- **The rim comes from a reference mesh.**
- **It produces meshes, not features.** The output is marching-cubes meshes, and the STEP files are faceted
  conversions with no feature tree.
- **No casting rules are applied.** Draft, wall thickness and hot spots are not checked.

**Training a generator on DeepWheel data.**
- **Too little data:** 904 3D designs are too few for a 3D generator.
- **Too few labels:** only two modal frequencies and mass.
- **Licence:** **CC BY-NC 4.0**. A model trained on it is likely a derivative, so it should be kept out of
  anything shown commercially. This is our reading, not legal advice.

**Better uses of the idea:**
1. **Images for style.**
   - Generate style images ourselves, from our own prompts and masks.
   - Fit our **parametric** spoke model to each image, by optimisation or a trained image-to-parameter encoder.
   - Where the fit leaves a gap, that gap shows which feature the parametric language is missing, and it becomes
     the trigger for the agent to invent one.
2. **Train our own generator on our own data.** Train a conditional generator over feature programs, conditioned
   on requirements and a style embedding. Its output is always editable and manufacturable by construction, and
   always graded.
3. **Use DeepWheel as a non-commercial benchmark.**
   - Compare style coverage against our designs.
   - Re-solve their designs with our grader, adding cornering and radial fatigue. This shows whether designs that
     pass on modes alone would pass qualification.

## What DeepWheel lacks (relative to our goals)

1. **Editable CAD.** Designs are meshes converted to STEP, with no feature tree and no design intent.
2. **Qualification physics.** Real wheels are qualified by:
   - cornering fatigue (SAE J328, ISO 3006);
   - radial fatigue;
   - impact (SAE J175, the 13° test).

   DeepWheel has only free-free modes.
3. **Manufacturability.** No casting checks: draft, wall thickness, isolated thick sections (hot spots),
   machining stock.
4. **Requirements and agents.** No requests, no agent, no decision traces, no verification record.
5. **Validated learning.** No trained surrogate is reported.
6. **Open licence.** The licence is non-commercial, so the data cannot be mixed into a CC BY dataset or a commercial
   product.

## Wheels against brackets for fastcae-sim (assessment)

| | Cast wheel | Bracket |
|---|---|---|
| Demo appeal | Very high: an iconic, styled part. A style prompt or sketch leads to a design that passes SAE tests | Good: the whole part changes and there's a gallery of concepts |
| Understood instantly | Yes, by everyone | Yes, by engineers |
| Link to the CEO (Raptor turbomachinery) | **Strong.** Cyclic symmetry, nodal-diameter modes, spoke/rim modes: the same analysis as bladed disks and impellers | Weak |
| Your NVH expertise | Strong: wheel and hub modes, tyre-cavity coupling, road noise | Strong: modes, random vibration, fatigue |
| Reuse of fastcae (GRC) learnings | **Casting rules** on a real cast part | Few |
| Requirements as numbers | Ideal. The interface is fixed by standards (PCD, bore, offset, rim contour, load rating) | Ideal |
| Real qualification tests | SAE J328 cornering and radial fatigue (linear static plus fatigue: feasible). SAE J175 impact (nonlinear explicit: hard) | ISO 16750-3 vibration and shock (linear: feasible) |
| FE cost per design | Tens of seconds to minutes. Roughly 0.5–1 M DOF for a full solid; cyclic symmetry cuts the modal cost (estimate) | Seconds |
| Live demo | Partly: screening is live, FE is a time-lapse | Yes |
| Physical anchor | Hard. Production wheels can't be made. Options: tap-test a real wheel to validate the grader, or a scaled printed model | Easy: cut, bend and tap-test real parts |
| Process choice | Low-pressure casting against flow-forming against forging | Wide: sheet, machined, cast, extruded, printed |
| Novelty against existing work | Crowded *in academia* (Kang lab, 2019–2025), but no parametric, fatigue-qualified, manufacturable, agentic version exists | Crowded in vendor demos; no sheet-metal vibration dataset exists |
| Existing baseline to beat | DeepWheel (904, modal only, NC licence) | SimJEB, DeepJEB (static, AM titanium) |
| Customers | Wheel makers, OEMs, motorsport, a large style-driven aftermarket | Automotive suppliers, EV, avionics, robotics, telecom |

**Design-space note.** A parametric wheel separates naturally into:
- a fixed rim contour (ETRTO/TRA profiles);
- a fixed hub interface;
- a spoke design language: spoke count, split or twin spokes, cross-section, curvature, windows, back-side lightening
  pockets, flange flare.

Style intent can be multimodal: a text prompt or reference image, mapped to these parameters by a vision-language
model. Diffusion images serve as inspiration, not as geometry. That keeps the CAD editable, unlike DeepWheel's
mesh-based route.
