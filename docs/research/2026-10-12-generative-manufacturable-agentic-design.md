# Generative, manufacturability-aware and agentic design: what six sources say, and a structure for zenryx

**12 October 2026, 13:42.** The engineer, 13:38, sent five links: "we are discussing same topic manufacturability aware, but still generative, still intelligent and still agentic… can we use these papers to give some structure to our thoughts and think more clearly taking guidance from literature." A sixth source, TopoDiff, was found while reading the MIT page.

How each was read:
- **GenTO** (arXiv HTML) and the **MethodsX** paper (Europe PMC's full text, PMC12355488; ScienceDirect refused the fetch): read through a page fetcher, which summarised them.
- **The designforam talk, the MIT project page and the Astraea page:** read in full the same way.
- **TopoDiff:** known from its abstract and search results only.

Check a value against its source before citing it in public.

## 1. In short

Every system of this kind answers five questions. The sources answer them differently, and zenryx's recurring failures sit in two of them.

| Question | What the sources do | zenryx today |
|---|---|---|
| **1. What can a shape be?** (representation) | Densities on a mesh (SIMP); a neural field, several shapes from one network (GenTO; not smooth by construction, [note 03](2026-10-12-reviewer-papers/03-gento-2025-neural-fields.md)); a signed-distance surface (MethodsX's smoothing, the plan's generator C); the latent space of a learned model (TopoDiff, Astraea); explicit features | A height field, each column one height off its wall (castable by construction), drawn as a signed-distance surface; the parts library (LOP-26) |
| **2. How are candidates made?** (generation) | Gradient optimisation; **several diverse near-optimal shapes in one run with a diversity constraint** (GenTO); sampling a model trained on optimised designs (TopoDiff, Astraea); an RL policy that edits the design with FE as the reward (MethodsX) | One optimisation at a time; variants made by hand-chosen rules |
| **3. Where does manufacturability enter?** | In the representation; as constraints (length scales); **as guidance during generation** (TopoDiff's classifier against floating material; MIT's graph-based constraints); as post-processing (MethodsX's smoothing, GenTO's floater removal); as hard checks | Castable along the pull by construction; the band and the least member as constraints. The look rules (no paint, no lumps, no worms) come after the run, as drawing choices and checks |
| **4. Who chooses the next step?** (agency) | A human; an RL policy over per-element actions (MethodsX, 2D only); an LLM agent calling deterministic tools, writing its justification, benchmarked on known problems (Bender) | Claude by hand, with a decision log and the Campaigns page; the agent's judgement not benchmarked |
| **5. How is it proven?** (verification) | FE on the generated geometry (GenTO, MethodsX); a graded benchmark of the agent (Bender); nothing shown (the Astraea page) | FE on the drawn mesh and the grade; a factor of safety for the optimiser's optimism |

**Where we keep failing: questions 1 and 3.**
- The representation lets the optimiser make shapes no foundry makes: paint, lumps, worms.
- Our rules against them come after the run: the drawing, the reading into parts, the checks.
- Every conversion after the run lost performance:
  - the skeleton, 3.3 times too soft;
  - this morning's parametric CAD, 4.6-5 times too soft;
  - the parts read from the gap-rule run, a tilt of 1.1-1.4 ×.

The sources that do better put the rule inside the representation or the generation:
- GenTO's smooth neural fields;
- TopoDiff's manufacturability guidance during sampling;
- MIT's constraints "integrated" in generation, "rather than as post-hoc filters".

## 2. The sources

### 2.1 GenTO: Diverse Topology Optimization using Modulated Neural Fields (arXiv 2502.13174, 2025)

- **What it does.** One neural network (WIRE, wavelet activations) takes a point and a 2D modulation vector z and returns a density there. Each z is a different shape, and the shapes are optimised together.
- **Diversity is a constraint inside the optimisation.** The distance between shapes is a differentiable chamfer distance between their boundaries. The aim is "Σ_j (min_{k≠j} d(Ω_j, Ω_k))^{1/2})²", held at a target by an adaptive augmented Lagrangian.
- **The physics.** FE in the loop computes each shape's compliance and its adjoint gradient. A Heaviside projection is sharpened from β 1 to 100 over iterations 0-400. SIMP's penalty is 1.5 in 3D (3 led to poor local minima).
- **Results** (version 2, 17 June 2025, which renamed the method TOM; read in full in [note 03](2026-10-12-reviewer-papers/03-gento-2025-neural-fields.md)):
  - mean compliance against plain SIMP's single design: +10 % (MBB beam), +17 % (cantilever), +32 % (3D bracket); the best sample −3 % to +8 %;
  - diversity 2.4-3.1 times the deflated-barrier method's;
  - the 3D bracket: 16,770 elements, 9 shapes, 47 min on a Titan V and a 36-core Xeon.
  - Version 1's MBB numbers (9 shapes in 4 min, +1.5 %) no longer stand.
- **Limitations stated.**
  - "Shapes can contain floaters … and surface undulations"; no length-scale or manufacturing control is built in.
  - The diversity depends on the size of the modulation space.
  - The method costs many solver calls.
- **What transfers to us.**
  - A population of distinct designs in one run, by a diversity constraint, instead of variants chosen by hand, at a cost of 10-32 % in mean compliance.
- **What doesn't.**
  - It is not a smooth representation: the authors chose a network biased to high frequencies and blame it for the waviness; no length scale is defined.
  - It has no casting rules, and its one 3D case is small (26 × 43 × 15 elements).

### 2.2 Kumar et al.: Reinforcement learning-based topology optimization for generative designed lightweight structures (MethodsX, 2025, doi 10.1016/j.mex.2025.103539)

- **What it does.** A PPO agent (a CNN actor-critic) sees a 2D design (60 × 40) with its displacement and stress fields, and keeps or removes each of the 2,400 elements. FE (FEniCS) is run at every step.
- **The reward:** −α·V + β/C when the stress (300 MPa) and the displacement (0.5 mm) hold, −100 otherwise.
- **After it:** signed-distance smoothing for printing, a 5 mm least wall, an overhang check, and FE again.
- **Results claimed.**
  - 40 % lighter, within both constraints.
  - Inference in 2.1 s against SIMP's 18.4 s. This compares a trained policy with an optimisation run from scratch, so it is not a like-for-like comparison.
- **Limitations stated.** 2D only; idealised materials and loads; "SDF filtering does not yet fully integrate constraints of specific additive manufacturing processes"; slow convergence and exploration in complex spaces.
- **What transfers to us.**
  - FE as the agent's reward.
  - A policy that learns which edits pay.
- **What doesn't.** Per-element actions do not scale to 100,000 voxels in 3D. For us the actions are operations, like the seven of 12 October 13:34.

### 2.3 Sergey Pigach (Thornton Tomasetti, CORE studio): Agentic engineering for generative design systems (designforam.com, 17 September 2026)

- **The system.** Agents ("Bender") work in Slack threads. They call the studio's engineering tools as cloud APIs over MCP, delegate to specialist agents (A2A), and deliver a design with a written justification. One example designs concrete columns and footings for five-storey buildings.
- **Verification.** A benchmark of 91 hard structural problems, graded within 1 %, solved with "nothing but a calculator and a Python sandbox": leading models score 94 % and more.
- **Its claims.**
  - The agent's advantage is the shared context of the thread.
  - Success depends on a "verifiable domain".
  - "This is not a domain expertise problem but an unhobbling problem."
- **Manufacturability:** hardly treated.
- **What transfers to us.**
  - Deterministic tools do the work and the agent justifies each choice, which is our rule already.
  - Benchmark the agent: a set of design situations with known good moves, against which its choices are graded.

### 2.4 MIT Generative AI Impact Consortium: manufacturability-aware generative AI for topology optimisation (Faez Ahmed, DECODE lab; Josephine Carstensen)

- **What it is.** A conditional diffusion transformer, with "structural performance metrics and graph-based manufacturability constraints" integrated in the generation, "rather than as post-hoc filters".
- **What the page lacks:** no method details, no results, no paper.
- **The group's earlier work, TopoDiff** (Mazé & Ahmed, AAAI 2023, arXiv 2208.09591).
  - A conditional diffusion model guided during sampling by surrogates: a compliance regressor and a floating-material classifier.
  - It gives an 8-fold reduction in performance error and an 11-fold reduction in infeasibility against a conditional GAN.
- **What transfers to us.** The manufacturability rule as guidance inside the generation. The guide can be a learned classifier of what a foundry accepts.

### 2.5 Astraea Software: Aries 3D, AI-driven topology optimization (astraea-soft.com)

- **What it is.** A conditional latent diffusion model trained on optimised structures (the OpenTO dataset; a foundation model, arXiv 2510.23667). It generates "10-50 diverse candidates in parallel" from loads, supports and a volume fraction, in "seconds to minutes".
- **Its claims (marketing, no data shown):**
  - "Near-optimal (~95-98% of classical)";
  - a UAV frame 35 % lighter.
- **What it lacks:** manufacturability only "learned during training", and suited to additive manufacture; no casting rules, no CAD, no verification shown.
- **What transfers to us.** A learned generator's style is its training set's. If it were trained on production housings, it would make production-looking housings. We have no such dataset. Our campaigns, each design FE-graded, are where one could come from.

## 3. What this means for zenryx

1. **Decide which look we want, because the sources split on it.**
   - A **production look** comes from prior knowledge: explicit features (our parts, MMC) or a learned style (TopoDiff and Astraea look like their training data).
   - **Discovery** comes from freedom: optimisation with only physics and manufacturing rules (GenTO, SIMP). Its shapes are clean at best, and often unfamiliar.
   - The engineer's plan (`zenryx_new_plan.md`) chooses discovery within hard rules, with features as possible outcomes (§2.1). Today we mixed the two: free optimisation, then forcing production features onto it.
2. **Put the shape rules inside the generator, not after it.** Every after-the-run conversion lost performance. The plan's generator C should be a representation that is smooth and member-like by construction, with its length scale and smoothness as settings ("alter regularisation", plan §4). Two candidate forms:
   - the height field on a coarse smooth basis;
   - a small neural field per half, as GenTO's.
3. **Make diversity a constraint of the optimisation** (GenTO): K housings optimised together, each held at a distance from the others. That replaces hand-chosen variants with distinct ones, at a cost of 10-32 % in mean compliance in GenTO's version 2 cases. The plan's population and its diversity score (§5, §6) come from it directly.
4. **Keep manufacturability in three places:**
   - **in the representation:** castable along the pull, which we have;
   - **as guidance or constraints during generation:** least member, greatest member, gap, and later a learned check of what a foundry accepts (TopoDiff's idea);
   - **as hard gates after:** `castable.py`, watertightness, the interfaces.
5. **The agent acts at the level of generators and operations** (plan §7), never voxels. Each move's record is a training example: the situation, the move, FE's verdict. A learned policy that picks moves, MethodsX's idea at the right scale, comes later. So do a benchmark of the agent's moves (Bender's idea).
6. **Verification does not change:** FE on the generated geometry decides. The optimiser's model is calibrated against FE (plan §2.5, §6 stage 2); for the parts it disagreed.

## 4. The next experiment this suggests

**K diverse housings in one optimisation (GenTO's idea, on our physics):**
- **The set-up:** the benchmark's, `it1_free_5.5kg` (5.63 kg, passes every graded line). That means 4 mm voxels, peak drive, the 24 mm band, the least member, and every tilt and bed held with the factor of safety 1.15.
- **Four housings optimised together.** Each is a smooth height field, its length scale a setting, held at a distance from the others in plan (their metal in different places by at least a set share).
- **The cost:** four FE solves an iteration, about four times one run: about 10-15 minutes at 4 mm. Building the diversity term and the smooth basis: about 2-3 hours.
- **Then:**
  1. FE on each of the four;
  2. the five scores of the plan (§6);
  3. the agent's step loop (13:33-13:34) on the best one or two: one housing, one change at a time, kept only if FE says it helped.

## 5. Sources

- GenTO: Diverse Topology Optimization using Modulated Neural Fields, arXiv 2502.13174 (2025): https://arxiv.org/html/2502.13174v1
- Kumar N K, Manasa C M, Pavan Kumar B K, Bali M: Reinforcement learning-based topology optimization for generative designed lightweight structures, MethodsX (2025), doi 10.1016/j.mex.2025.103539: https://www.sciencedirect.com/science/article/pii/S2215016125003838 (read at Europe PMC, PMC12355488)
- Pigach S: Agentic engineering for generative design systems, designforam.com (17 September 2026): https://www.designforam.com/p/agentic-engineering-generative-ai
- MIT GenAI Impact Consortium, Ahmed F, Carstensen J: Manufacturability-aware generative AI for next-gen topology optimization: https://genai.mit.edu/manufacturability-aware-generative-ai-for-next-gen-topology-optimization/
- Mazé F, Ahmed F: Diffusion models beat GANs on topology optimization (TopoDiff), AAAI 2023, arXiv 2208.09591: https://ar5iv.arxiv.org/html/2208.09591
- Astraea Software: AI-driven topology optimization (Aries 3D): https://www.astraea-soft.com/en/ai-driven-topology-optimization-en/
