# The problem: mechanical design does not scale

*Problem statement, 2026-10-05. This document describes the problem only. It deliberately proposes no solution.*

## In short

Mechanical parts are still designed by hand, one iteration at a time. An engineer turns an intent into geometry, sets up
an analysis, reads the results, changes the geometry and repeats, guided by a limited set of physical principles and
rules of thumb. Most of the effort goes into these low-level iterations rather than into ideas, and only a handful of
alternatives are ever explored.

AI could take over that loop, but today it cannot be trusted to:
- requirements arrive incomplete;
- generated geometry is often unmanufacturable or wrong;
- physics evaluation fails without warning;
- the data needed to learn design does not exist in usable form.

We study this problem on one concrete, ubiquitous part, **the bracket**, from the standpoint of structural mechanics
and vibration (NVH).

## Goal

These are the outcomes we want, not methods.

1. **Intent in, verified design out.** An engineer states what a part must do, in plain language and with the
   surrounding CAD, and receives designs that:
   - can be manufactured;
   - demonstrably meet the requirements;
   - come with evidence an engineer would accept.
2. **The engineer keeps the judgment, not the drudgery.**
   - Geometry changes, analysis set-up and result checking happen without the engineer.
   - Intent, decisions and sign-off stay with the engineer.
3. **Every iteration becomes knowledge.** Every design explored, including the failures and the reason for each
   change, is kept in a form that makes the next design faster and better.
4. **Wider than a human would search.** The designs considered go beyond what an engineer has time to try, and
   "new and better" is measured rather than claimed.

## Motivation

### Where engineering time goes
- Design is a loop that crosses tools: CAD, meshing, solver, post-processing, then back to CAD. Every crossing needs
  manual set-up.
- Most loops are small: change a thickness, move a hole, add a rib, re-run, re-read.
- Time allows only a few concepts, so the first design that works is often the one that ships. It is usually heavier
  and more conservative than it needs to be.
- Late changes, such as a module moving or a load case being added, restart the loop, often under schedule pressure.
  Problems then surface late, in testing or in the field.

### Why rules of thumb are not enough
- Engineers rely on simplified models and rules of thumb because full analysis of every option is too slow.
- Some rules of thumb encode real constraints, such as what a press brake can bend. Others are just habit. Telling them
  apart takes experience that is rarely written down.
- Simplified models are valid only within limits, and outside them they give confident, wrong answers. Knowing which
  model to trust for which question, and when to move to a fuller one, is expert knowledge that tools do not capture.

### Why now
- AI agents built on large language models can now operate software: they write code, call solvers and read results.
- Physics AI models can predict simulation results orders of magnitude faster than solvers.
- Investment in both is growing quickly, but the pieces do not yet add up to design an engineer can trust.

## The problem in detail

### 1. Intent is incomplete
- Natural-language requirements leave out most of what geometry needs:
  - the interfaces;
  - the space available;
  - the load environment;
  - the manufacturing process;
  - the applicable standards.
- Missing information gets filled in silently, and unstated assumptions, such as boundary conditions nobody specified,
  are a common source of wrong results.

### 2. Geometry must be real, not just plausible-looking
- A usable design must:
  - be manufacturable by a specific process;
  - fit its interfaces and the available space;
  - remain editable by engineers afterwards.
- Geometry that looks right often violates the specification.

### 3. Physics evaluation fails silently
- An analysis can run without errors and still be wrong. Common causes:
  - unit mistakes;
  - missing constraints or wrong boundary conditions;
  - an unconverged mesh;
  - a model used outside its valid range.
- Recent studies of AI agents driving simulation and CAD tools report this repeatedly: many runs execute but are
  physically wrong or violate the specification.
- A system that cannot tell a correct result from a plausible wrong one cannot iterate safely. Anything that learns
  from its output inherits the errors, at scale.

### 4. Speed and accuracy pull in opposite directions
- Full-fidelity analysis is accurate but slow.
- Simplified models are fast but valid only in limited regimes.
- Learned predictors are fastest, but reliable only for designs similar to those they learned from.
- Nobody records, at scale, where each simplified model can be trusted for a given class of part.

### 5. The data does not exist
- Learning to design requires many designs with consistent physics labels.
- Public engineering datasets are few and narrow. They often cover one part family and static loads only, with no vibration results, little
  manufacturing realism, and no record of how each design was built.
- Industrial design data is proprietary, scattered across tools and inconsistently labelled. It almost never records
  failed designs or the reasoning behind changes, which is the most instructive part.

### 6. Reliability and innovation pull in opposite directions
- Restricting generation to known design patterns makes results reliable, but it only reproduces what engineers already know.
- Unrestricted generation can produce new shapes, but mostly invalid or unmanufacturable ones.
- There is no accepted way to measure whether a design is genuinely new and also better.

### 7. Learning from experience can drift
A system that learns from its own output can narrow its range of ideas, or learn to exploit weaknesses in how
designs are evaluated, unless it stays anchored to independent physical truth.

## Why brackets

- **Everywhere.** Vehicles, aircraft and machines each contain many brackets holding modules, sensors, harnesses and
  pipes.
- **Small but genuinely multi-physics.** A bracket must:
  - keep its payload clear of resonance;
  - survive random vibration (fatigue) and shock;
  - carry its loads through bolted joints;
  - conduct heat away from the module;
  - fit a cramped space;
  - be cheap to make.
- **Failure-prone.** Vibration fatigue of brackets and mounts is a classic field failure, and resonance problems often
  appear late, in qualification testing.
- **Iteration-heavy.** Brackets are often designed late, around packaging changes, and in many variants. That is
  exactly the repetitive work that should be automated.
- **Tractable.** A full-fidelity analysis of one bracket takes seconds to minutes on a laptop, so very many designs
  can be evaluated honestly.
- **Rich enough to matter.**
  - The geometry allows real innovation: stiffening features, closed sections, changes of load path, isolation.
  - The physics forces real modelling choices, such as a single mass on a spring versus a full modal analysis.
- **Rooted in structural dynamics and NVH**, where choosing a reduced-order model and knowing its limits is everyday
  practice.
- **Representative.** Every mechanical part family has the same ingredients: incomplete intent, manufacturable
  geometry, coupled physics, silent failure modes and missing data. Solving the problem properly for brackets is a
  blueprint for the rest.

**Scope:**
- **In:** mounting brackets for payloads such as electronic modules, under structural and vibration requirements. This
  includes the heat path through the bracket and manufacturability for its production process.
- **Out, for now:** multi-part assemblies, fluid-dominated physics, crash and other strongly non-linear events.

## Perspective

- **Physics first.** The aim is not to bypass physical reasoning but to apply more of it, faster. A design is only as
  trustworthy as its evaluation.
- **Engineers stay in charge.** Machines take over the repetitive loop. Engineers own the intent, the judgment and the
  sign-off.
- **Evidence over assertion.** Every claim needs evidence an engineer can check: that a design passes, that a model is
  valid, that a design is new, that it is better.
- **Failures are information.** Designs that don't work, and the reasons why, are as valuable as those that do.
- **Honest about limits.** Simulation is not measurement. Assumptions, such as damping, must be explicit.

## Outlook

- **Near term.** For one class of part, the path from intent to a verified, manufacturable design runs without manual
  iteration, and produces reusable knowledge as it runs.
- **Next.** More part families, more physics (fluid flow, heat transfer, aerothermal loads), and assemblies whose parts
  interact.
- **Long term.** Engineers describe what a system must do, and machines handle the low-level design. Engineering hours
  limit how much mechanical complexity people can design today; that limit rises.

## Questions the work must answer

Answering these is the work. This document does not attempt to.

1. How can incomplete natural-language intent become a complete, checkable specification, without silent assumptions?
2. How can a design's evaluation be made trustworthy enough to automate on, and to learn from?
3. For a given design, how do we know whether a simplified physical model can be trusted?
4. How can many manufacturable, physically meaningful designs be produced without designing each one by hand?
5. How can designs go beyond known patterns, and how is "new and better" measured?
6. How should a design be represented so that machine-learning models can learn from it?
7. How can a system improve from its own experience without drifting away from physical truth?

## What "solved" looks like, for brackets

- Realistic bracket requests return verified, manufacturable designs without manual iteration, with margins,
  assumptions and model validity stated.
- The evaluation demonstrably catches its own errors.
- The knowledge produced, successes and failures alike, can be reused by others.
- Some designs are measurably both new and better than conventional solutions.

## Background

The research behind this statement is in `docs/research/2026-10-04-ai-cae-landscape.md`. It covers AI agents for CAD
and simulation, the failure modes reported for them, and existing datasets. Individual citations must be verified
before publication.
