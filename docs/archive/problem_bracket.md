# Open problem: AI that designs verified brackets from plain-language requirements

*A problem brief for outside perspectives, 5 October 2026.*

This document describes a problem, why it matters, and what we want to achieve. **It deliberately contains no
solution, and it does not fix the manufacturing process.** We have early ideas of our own and have left them out so
as not to anchor yours.

## Why we are sharing this

We want perspectives that are different from ours:
- approaches we haven't considered;
- research we may not know about;
- tools, datasets and pitfalls;
- challenges to the way we have framed the problem.

Ideas from mechanical engineering, machine learning, optimisation, manufacturing, or anywhere else are welcome.
Section 11 explains how to respond.

---

## 1. In short

Mounting brackets are among the most common mechanical parts. They hold electronic modules, sensors and other
equipment to the structure of a vehicle, aircraft or machine. They are made in many ways: bent sheet metal,
machined plate, castings, extrusions, 3D-printed metal or polymer, composites. A good bracket has to balance:
- vibration;
- fatigue;
- shock;
- heat;
- mass;
- cost;
- manufacturability.

Today, engineers design brackets by hand through slow iterations, and usually commit early to a familiar process
and concept.

**We want AI that:**
- takes an engineer's plain-language requirement;
- returns several manufacturable bracket designs, possibly in different processes and materials, each verified
  against the requirements and explained by physics;
- learns from every design it explores, successes and failures alike;
- gets faster, more reliable and more inventive over time.

## 2. How brackets are designed today

1. An engineer receives requirements: the module, where it mounts, the vibration and shock environment, the
   temperatures, the space available, the production volume, and targets for mass or cost.
2. The manufacturing process is often chosen early, by habit or by the supplier base, before alternatives have been
   compared.
3. They pick a concept from experience and rules of thumb, model it in CAD, set up a finite-element (FE) analysis,
   run it, read the results, change the design, and repeat.
4. Every loop crosses several tools and needs manual set-up. Boundary conditions, units and assumptions are easy to
   get wrong without anyone noticing.
5. Only a few concepts are explored, usually in one familiar process, so the first design that works is usually the
   one that ships. It is often heavier, costlier or more conservative than it needs to be.
6. Resonance and fatigue problems often appear only in qualification testing, which is late and expensive.

## 3. Motivation

- **Scale.** Every vehicle, aircraft, robot and machine contains many brackets, so small improvements multiply.
- **The cost of failure.** Resonance and vibration fatigue are classic field failures of brackets and mounts.
- **Wasted expertise.** Engineering time goes into low-level iteration rather than ideas.
- **Missed options.** Comparing processes and materials properly takes too long, so the choice is rarely revisited.
- **The opportunity now.**
  - AI agents can now operate engineering software.
  - Machine-learning models can predict simulation results very quickly.
  - Neither can yet be trusted on its own. Results that look plausible but are wrong are common, and there is
    little suitable data to learn from.
- **A good proving ground.** The bracket is:
  - ubiquitous;
  - multi-physics;
  - iteration-heavy;
  - fast to simulate;
  - rich enough in geometry, materials and processes to allow real invention;
  - cheap to make and test physically.

  An approach that works here should carry over to other kinds of part.

## 4. The task, precisely

### 4.1 Inputs

| Input | Content |
|---|---|
| **Request** | Plain language, written by an engineer, possibly incomplete |
| **Interfaces**, as fixed numbers | Bolt holes on the structure (positions and size). The payload's mass, centre of gravity, footprint, bolt pattern and power dissipated |
| **Environment** | A random-vibration profile (a power spectral density from a standard), a shock pulse, static g-loads, ambient temperature |
| **Requirements** | <ul><li>a minimum first natural frequency</li><li>fatigue life under the vibration profile</li><li>shock and static strength margins</li><li>bolted joints that don't slip or separate</li><li>a maximum module temperature</li><li>mass or cost limits</li></ul> |
| **Space** | An allowed envelope, keep-out zones, tool access to the fasteners |
| **Manufacturing** | The processes and materials that are allowed or preferred, with their design rules, or left open for the system to choose. Processes include sheet metal, machining, casting, extrusion, additive manufacturing and composites. Production volume |
| **Program context** | The standards, material data and design rules that apply |
| **Objective** | Lightest, cheapest at the stated production volume, or a stated trade-off |

**No CAD of the surroundings is required.** The bolt and payload locations are fixed numbers in the specification.
That mirrors the convention of the GE Jet Engine Bracket Challenge.

**The process may be fixed or open.** A program may fix the manufacturing process or leave it open. When it is open,
choosing the process is part of the design problem.

### 4.2 Outputs

- **Several distinct candidate designs**, not one. They may use different processes and materials.
- **For each candidate:**
  - **editable parametric CAD** that an engineer can open and change;
  - **manufacturing data suited to its process:** drawings, plus process-specific data such as flat patterns for
    sheet metal, or draft and parting information for castings;
  - **a verification record:** for every requirement, the value, limit, margin, the model used, whether that model
    was valid, and the assumptions;
  - **a physics explanation:** what governs the design, why it works, and why the alternatives were rejected.
- **If candidates use different processes:** a fair comparison of cost, mass and risk at the stated production
  volume.
- **If the request is impossible:** a clear "not possible", with the physical reason and the nearest feasible
  alternatives.
- **If information is missing:** questions, not silent assumptions.

### 4.3 Example requests

1. **Complete, driven by stiffness:** "Mount a 1.2 kg, 15 W control module to the vertical body rail, 2 × M6 bolts
   80 mm apart. ISO 16750-3 body vibration. First mode ≥ 200 Hz, module base ≤ 85 °C. Lightest aluminium."
2. **Driven by isolation:** "IMU on the firewall: cut vibration above 100 Hz by at least 70 %; sway under 3 mm."
3. **Cost and heat:** "3.5 kg inverter controller spanning two floor rails 200 mm apart, 40 W, base under 90 °C.
   Cheapest steel bracket."
4. **Incomplete:** "Need a bracket for a small controller on the rail; should survive vibration."
5. **Possibly impossible:** "1.2 kg, 15 W module; base ≤ 70 °C at 65 °C ambient; the bracket is the only heat path."
6. **Process left open:** "0.8 kg sensor box on the engine block, first mode above 400 Hz, 50,000 units a year.
   Choose the process and material."

## 5. What we want to achieve

| Goal | What it means |
|---|---|
| **G1. Intent in, verified designs out** | An engineer states the requirement once and receives several manufacturable, verified designs. The engineer keeps the judgement and the sign-off |
| **G2. Physics first** | For each design, the system states the governing parameters, which requirement binds, and why. Simplified models are used only where they are known to be valid |
| **G3. A self-directing data engine** | Verified design data keeps being generated with little human effort, and the system decides what is most valuable to generate next. It records failures, design changes and the reasoning behind them, not only successes |
| **G4. Learning that compounds** | The data trains fast physics predictors and better design agents. Each round is measurably faster, cheaper or more reliable, and the system knows when its fast predictions should not be trusted |
| **G5. Measurable creativity** | Designs go beyond conventional patterns, including concepts, materials and processes an engineer would not have tried. "New and better" is measured rather than claimed |
| **G6. Trust and reproducibility** | No silent errors. Assumptions are explicit, and every claim can be reproduced |

## 6. What makes it hard

- **C1. Incomplete intent.** Requests leave out loads, environments, interfaces or process limits. Filling the gaps
  silently is a common source of wrong results.
- **C2. Real geometry, not plausible shapes.** Designs must be manufacturable by their process and editable by
  engineers, with the design intent preserved. Each process has its own rules: bend radii, draft, tool access,
  minimum walls, overhangs. Geometry that merely looks right often violates the specification.
- **C3. Silent simulation failure.** An analysis can run without errors and still be wrong because of units, missing
  constraints, unconverged meshes, or a model used outside its valid range.
- **C4. Speed against accuracy across several physics.** Modal response, random vibration, fatigue, shock and heat
  transfer each have fast approximations whose validity varies from one design to the next. Nobody knows, at scale,
  where each approximation can be trusted.
- **C5. Inherent physical uncertainty.** Damping, bolted-joint stiffness and thermal contact conductance are
  uncertain by nature, so designs must be robust to them. Process-dependent material properties add to this, for
  example in castings and printed parts.
- **C6. Data scarcity.**
  - **What exists:** the public bracket datasets are SimJEB (381 human designs), DeepJEB (2,138 generated designs)
    and DeepJEB++ (15,360, announced).
  - **What they cover:** titanium brackets shaped for additive manufacturing, under static loads.
  - **What none of them has:** other manufacturing processes, vibration fatigue, thermal results, plain-language
    requirements, design programs or design reasoning.
  - **Industrial data** is proprietary, and it rarely records failures or why changes were made.
- **C7. Reliability against innovation.** Generating only from known patterns is reliable but unoriginal. Generating
  freely is original but mostly invalid.
- **C8. Learning without drift.** A system that learns from data it generated itself can narrow its ideas, or learn
  to exploit weaknesses in how designs are evaluated.
- **C9. Evaluating agents.** Design agents are non-deterministic and work in many steps. Success has to be measured
  across repeated attempts:
  - how often at least one attempt succeeds;
  - how often every attempt succeeds;
  - what each success costs.

  Failures have to be diagnosed down to the step that caused them.
- **C10. Synthetic against real.** Generated requirements and designs must resemble real programs, and predictions
  must hold up against physical tests.
- **C11. Choosing the process.** The process and material decide what geometry is possible, and also the cost, mass
  and lead time. The best choice depends on production volume. Comparing designs fairly across processes is hard.

## 7. Constraints

- **What "verified" means.** A requirement counts as verified only when full-fidelity simulation (or a physical
  test) checks it, with the assumptions and model validity stated. Faster approximations may guide the search, but
  they may not sign a design off.
- **Honest scope.** Nothing that wasn't specified may be claimed. For example, without a shock load there is no
  shock qualification. Engineers approve the results.
- **Outputs.** Editable parametric CAD plus manufacturing files, manufacturable by the stated or chosen process.
- **Open and reproducible.** Code plus configuration reproduces every result. Open-source, scriptable tools are
  preferred. Published data must be our own, with no third-party proprietary designs.
- **Resources.** A small team (one engineer working with AI coding agents), one GPU workstation, a modest cloud
  budget, and first results within weeks.
- **Reality checks.** Simulation is not measurement. Physical tests on a few designs, such as tap tests that
  measure the first natural frequency, are feasible.

## 8. What success looks like

- **Representative requests are handled well**, including request types never used during development:
  - each gets several distinct, manufacturable, verified, explained designs;
  - impossible requests are recognised;
  - missing information is asked for.
- **Processes are compared fairly.** Where the process is open, designs in different processes are compared at the
  stated production volume.
- **The data engine earns its place.** At equal compute, it produces more useful data than a fixed sampling plan:
  wider coverage, more distinct concepts, better predictor accuracy on unseen request types, and more errors caught.
- **Fast predictors are measured.** Their error, and how often they wrongly pass a failing design, are known on
  unseen request types.
- **Learning measurably improves the agent:** success across repeated attempts, and the cost and time per verified
  design.
- **Some designs are both novel and better** than conventional ones, by explicit measures.
- **Physical tests agree** with the predictions within the stated uncertainty.

## 9. Where we would most value ideas

- **Q1. Representation.** How should bracket designs be represented so that learning generalises across very
  different shapes and manufacturing processes, and the result stays editable and manufacturable?
- **Q2. Generation.** How can we produce many diverse, manufacturable, physically meaningful designs, including
  genuinely new concepts?
- **Q3. Trustworthy evaluation.** How can silent simulation errors be detected automatically? How can we know when a
  simplified model is valid for a particular design?
- **Q4. Budget allocation.** How should a limited simulation budget be split across fidelity levels and candidates?
- **Q5. Physics AI for dynamics.** How can we predict mode shapes, random-vibration response and fatigue across
  changing geometry and topology, with uncertainty we can trust?
- **Q6. Agents.** How can an agent be taught good engineering decisions, as opposed to plausible ones? How should it
  be evaluated, and how do we stop it gaming the evaluation?
- **Q7. Novelty.** How can we measure novelty that an engineer would actually value?
- **Q8. Realism.** How can we make synthetic requirements and designs realistic, and validate them cheaply?
- **Q9. Uncertainty.** How should uncertain damping, joint stiffness, contact conductance and process-dependent
  material properties be handled?
- **Q10. Process and material selection.** How should the system choose among processes and materials, and compare
  designs fairly across them at a given production volume?
- **Q11. Anything else.** What would you do differently? Is this the right problem?

## 10. What we know so far

These are pointers, not a survey. Please tell us what is missing.

- **Bracket datasets:**
  - [SimJEB](https://arxiv.org/abs/2105.03534): 381 designs, 4 static load cases;
  - [DeepJEB](https://arxiv.org/abs/2406.09047): 2,138 designs, 4 static load cases plus the first two free-free modes;
  - [DeepJEB++](https://arxiv.org/abs/2606.12994): 15,360 designs, announced;
  - all three follow the [GE Jet Engine Bracket Challenge](https://grabcad.com/challenges/ge-jet-engine-bracket-challenge).
- **AI writing CAD code from text.** [RealCADBench](https://arxiv.org/abs/2609.03773) (2026) gave 12,632
  industrial design-intent tasks to 9 frontier models. Executability ranged from 0.57 to 0.81, and solid IoU from
  0.28 to 0.54.
- **Generative design.**
  - Topology optimisation suits additive manufacturing and casting.
  - [Topography optimisation](https://help.altair.com/inspire/en_us/topics/inspire/tutorials/tut_opti_topography_c.htm)
    produces bead patterns on sheet metal that raise stiffness and natural frequency without adding mass.
- **AI agents driving CAD and simulation software.** These exist. Published studies report frequent results that
  run but are physically wrong, and that are seldom checked for physics or manufacturability.

## 11. How to respond

Any form is welcome. The most useful structure is:

- **The idea**, in one or two sentences.
- **What it addresses:** the goal, challenge or question it targets (G1–G6, C1–C11, Q1–Q11).
- **Why it might work**, with evidence or references.
- **What it needs:** data, tools, compute, expertise.
- **How to test it quickly.**
- **Risks, or where it could fail.**

We also welcome:
- arguments that we are solving the wrong problem;
- pointers to people, groups, papers, tools or datasets.

**Contact:** *(to be added)*

## Glossary

- **First mode, natural frequency.** The lowest frequency at which the structure resonates. Requirements set a
  minimum, to stay clear of the frequencies where the input vibration is strongest.
- **Random vibration, PSD.** Broadband vibration described by its power spectral density, as defined in test
  standards.
- **Fatigue damage.** Damage accumulated under cyclic stress. A value of 1 means expected failure; requirements
  keep it well below that.
- **Shock.** A short, severe acceleration pulse, for example a half-sine.
- **Flat pattern.** For sheet metal, the unfolded sheet that is cut before bending.
- **Draft.** For cast or moulded parts, the taper that lets the part leave the mould.
- **NVH.** Noise, vibration and harshness.
- **FE.** Finite-element analysis.
