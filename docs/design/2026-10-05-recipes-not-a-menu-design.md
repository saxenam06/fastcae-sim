# Recipes, not a menu: fastcae designs any casting by writing its members

**Date.** 5 October 2026.

**Status.** Draft, for the engineer's review. Nothing here is built yet.

**Where it will live.** It is written in `fastcae-sim` because that was the folder open for writing. Once the
engineer agrees, it moves into fastcae as a new feature page with its PBIs (key proposed: **REC**).

**Built on:**
- fastcae's own designs: [member-and-geometry.md](../../../../fastcae/docs/member-and-geometry.md) and
  [part-model.md](../../../../fastcae/docs/part-model.md).
- The audit of 4 October: [2026-10-04-fastcae-audit-for-mekint.md](../../research/2026-10-04-fastcae-audit-for-mekint.md).

Paths to code are relative to `C:\Work\fastcae`; `S` = `src/fastcae`.

---

## 1. The goal

**In one sentence.** An agent designs a casting by **writing** its members, as a recipe, anywhere the part
allows; it no longer **picks** from a menu built in advance for one part. Physics guides it, the casting rules
check every member, and FE proves every design. This is shown first on the GRC gearbox housing, then on a
bracket with nothing written for the bracket.

**What "reached" means.** All four must hold:

1. **On the housing.**
   - The recipe agent does at least as well as today's menu agent, in a controlled benchmark (one frozen commit,
     repeats, the spread reported).
   - At least one design that meets the goal uses members the menu never held.
2. **On the bracket.**
   - Inputs: its CAD, its load cases, a process profile and a goal.
   - From those, rule-valid, FE-proven designs that meet the goal, within one working day of setup.
   - Nothing in `src/` written for the bracket.
3. **One data format.**
   - Both parts' designs are recorded as recipes and as tokens a network can read, the same on every part, made
     by a frozen pipeline.
   - A first fast model is trained on them and tested across the two parts.
4. **Every claim reproducible.** Each claim can be rebuilt from a commit and a config. The bracket, which is
   licence-clean, becomes the public showcase.

**Why.**
- **For the product:** today it can only recombine what was pre-built for one housing.
- **For the MEKINT application:** this is their "synthetic geometry generation through automated CAD operations"
  and their "embedding-friendly representations", shown working.
- **For the engineer's own designs:** it finishes what member-and-geometry.md set out: "the gearbox housing, a
  bracket, a knuckle and a motor mount go through the same code", and its proof step 6, "the same code on a
  bracket's own CAD ... with nothing written for it".

## 2. Where we are today

### What works (verified 4 October)

- **The part model** reads the CAD and the deck into typed entities: faces, walls, bores, bosses, holes and their
  tool spaces, axes (`S/part/model.py`, `walls.py`, `rays.py`).
  - **The geometry context** answers distance, ray and containment questions (`S/geometry/context.py`,
    `exact.py`, `surface.py`).
- **A member is already a handful of numbers.**
  - `MemberSpec` (`S/member/spec.py:84`) holds two anchors, a curved path, a base line, three top heights,
    thickness, draft, sink, caps and the kind (web or plate), plus flange options: T-section, inverted T-section,
    narrowing.
  - The exact solid is drawn from those numbers alone (`S/member/solid.py`).
- **The rules** answer every member PASS/FAIL/UNKNOWN with margins, FAST on the GPU or EXACT on the B-rep
  (`S/rules/member.py:105`, `result.py`, `attach.py`).
- **The pipeline:**
  - CP-SAT keeps legal sets of members.
  - OpenCascade fuses them into STEP and BREP.
  - gmsh meshes face by face (TET10, fillets rolled on).
  - cuDSS solves in about 35-45 s.
  - Each design keeps a manifest.
- **The agent** is Claude Code, headless, in a strict harness, driving 7 tools.
  - It met production's stiffness within mesh noise with 3.2 % less rib metal on the CAD (design 04 of
    `opt-20261002-073129`).
  - These are single runs, not yet a controlled benchmark.

### What limits us

| Today | How it limits us |
|---|---|
| **A menu.** Members are laid on patterns, judged, and kept as a library before any run. Library `b844caed37325549`: 805 laid, 673 placed, about 1.5 h to build (`S/pipeline/library.py`). The agent's moves - topology, add, swap, replan, restart - only switch library members on and off (`S/optimize/agent.py`) | The agent can recombine, never invent. A member that is not in the menu cannot be tried. A new idea - a new family, a new pattern - means engineering and a rebuild: the inverted T-section took more than a day |
| **Anchors on hand-picked rails.** A member's ends are positions on the rails of design volumes the engineer picked (S1, S2, S3 ceiling). `MemberSpec` holds absolute points `a`, `b` and the CAD's face indices `hosts` | It does not carry over to another part. Face indices change when a CAD is exported again. Every new part needs volumes picked by hand before anything runs |
| **A design is a list of library ids and thicknesses** (`design.json`: `members[{id, thickness_mm}]`) | It means nothing outside its library. No model can learn across parts from it, and a dataset of one part cannot teach another |
| **Physics guides only inside the menu.** Topology acts on the library's member presences, not on the part (`S/loop/relax.py`) | The physics can say which menu member pays, never where a member that is not there would pay |
| **One part, one load case, linear statics.** Code hard-codes the housing in places: `S/loop/__main__.py:37`, `S/simulate/face_mesh.py:52`, `S/generate/objective.py` | A bracket with four load cases cannot run today |
| **Records not yet a dataset.** 369 FE-solved designs, but 399 of 460 manifests are from uncommitted code; the campaign sampler runs CP-SAT with 8 workers, so it is not repeatable | Nothing can be trained or compared cleanly yet |
| **The repository is not self-contained.** The mesher imports a file from `C:\Work\agenticCAE` (`S/simulate/face_mesh.py:52,134-146`); tests are untracked; there is no CI | A clone cannot run, and a reviewer sees no tests |

## 3. Where we want to reach

### At run time - plain Claude Code, no training needed

```
"20 % less rib metal, no softer at the main bearing, keep S1 empty"       ← the engineer's words
   │
 1 LLM    words → the goal in numbers, asking about what is open                     (S3)
 2 TOOL   characterize: where the part bends and why; which seat and direction
          governs the goal                                                           (S3)
 3 TOOL   where metal helps: a field over the part, and candidate recipes laid
          along it                                                                   (S2)
 4 LLM    writes or edits a RECIPE - members on the part's own regions               (S1, S2)
 5 TOOL   resolve → MemberSpec → rules FAST, then EXACT → refusals come back with
          the rule and the place                                                     (S1)
 6 TOOL   quick estimate on the cube model, by the parent's own FE ratio             (exists)
 7 TOOL   build → STEP → mesh → FE                                                   (exists)
 8 LLM    compare with the goal → done, or back to 4
   │
OUT: STEP + FE + recipe + the reason behind every step
```

### What a recipe is

A recipe is the design as intent: which members, on which of the part's regions, what shape and size. It is a
few lines the agent can write and read. Everything derived from the part (3D points, CAD faces, cap planes,
sink) is computed by the resolver, never written by hand.

An example on the housing. The region ids are illustrative.

```json
{
  "recipe": "1.0",
  "part": { "name": "GRC_Gearbox_Housing", "cad": "sha256:…" },
  "process": "sand-cast ductile iron (the housing's rules record)",
  "members": [
    { "id": "m1", "kind": "web",
      "ends": [ { "region": "W-017", "near": "boss:B7", "s": 0.42 },
                { "region": "W-031", "near": "bore:main", "s": 0.10 } ],
      "path":   { "bend": [0.33, 12.0, 0.67, -8.0] },
      "base":   { "on": "F-S2" },
      "top_mm": [60, 75, 60],
      "thickness_mm": 20, "draft_deg": 1.5 },
    { "id": "m2", "kind": "inverted_tee",
      "ends": [ { "region": "W-012", "s": 0.55 }, { "region": "W-031", "s": 0.62 } ],
      "base":   { "level_mm": [0, 0] },
      "top_mm": [90, 90, 90], "thickness_mm": 15,
      "flange": { "width_mm": 60, "thick_mm": 15 } }
  ]
}
```

### What does not change

- FE stays the judge.
- The rules record keeps its values and meanings.
- The claim stays *rule-valid*, not *castable*.
- The agent never draws geometry: it writes recipes.
- One heavy job at a time on the laptop.
- The menu agent stays runnable: it is the benchmark's reference arm.

## 4. The design

### 4.1 Layers

```
recipe (intent: members on regions)                      NEW   written by the agent or a generator
   │  resolver - reads the part model                    NEW
   ▼
MemberSpec (numbers in the part's frame)                 EXISTS S/member/spec.py
   │  rules FAST, then EXACT; refusal = rule + place     EXISTS S/rules/
   ▼
member solid → fuse → STEP/BREP                          EXISTS S/member/solid.py, S/generate/cad.py, fuse.py
   │
   ▼
mesh (TET10, fillets rolled on) → FE (cuDSS)             EXISTS S/simulate/, S/generate/solve.py
   │
   ▼
record: recipe + tokens + results + decision             EXTEND S/lineage.py, S/generate/records.py
```

### 4.2 Recipe v1

| Field | Meaning | Maps to `MemberSpec` |
|---|---|---|
| `kind` | `web`, `plate`, `tee`, `inverted_tee` - today's four families | `kind`, `flange`, `flange_at_base` |
| `ends[2]` | each end: a host `region`, a position `s` along the region's trace in the member's plan (0-1), optional `near` (a named feature the tools snap to) | `a`, `b`, `hosts`, `caps` (resolved) |
| `path.bend` | the two inner control points: share along the chord, mm across it | `bend` |
| `base` | `on` a floor region (it stands, sinks into the floor), or `level_mm` at each end: along the pull, up from the lower edge of that end's region, so 0 sits flush on it as production's S2 flanges do (it hangs) | `base`, `sink`, `base_host`, `flush_base` (resolved) |
| `top_mm[3]` | heights over the base line at end, middle, end | `heights` |
| `thickness_mm`, `draft_deg` | within the process profile; draft defaults to the profile's | `thickness`, `draft_deg` |
| `flange` | width, thickness, narrowing and taper toward each end | `flange*`, `taper`, `narrow` |
| `holes`, `pads`, `thicken` | today's other pieces, carried as they are | as today |

**Rules for the format.**
- Versioned (`"recipe": "1.0"`) and validated by a schema: typed, in units, every number bounded by the process
  profile.
- A recipe never holds anything the resolver computes.
- Two recipes that resolve to the same members hash the same.

### 4.3 Host regions and anchors

- **A host region** is one wall, floor or ceiling as member-and-geometry.md defines it: the faces meeting along
  edges where the normals turn less than the surface's smooth turn. A round under the fillet rule is a region of
  its own.
  - The part model lists them once per CAD, each with an id and a descriptor: its kind, area, centroid, normal,
    the metal behind it, the features it carries (boss, bore, bolt hole), and its distance to each load and
    support of the deck.
- **Ids are stable within one CAD digest.** They are derived in a fixed order from the geometry, not from the
  CAD's face order. Re-attaching to a revised CAD stays *later*, as member-and-geometry.md says.
- **An anchor is (region, s).** `s` runs along the region's trace, from 0 to 1 by arc length: the curve where the
  region meets the plan square to the pull, at the height of the design volume's band. This is today's rail, read
  per region instead of per hand-picked volume, so today's ends are one case of it.
  - `near` lets the agent write "near boss B7", and the tools return the `s` that grips there.
- **Design volumes stay**, as where metal may go: the "inside the design volume" rule. They no longer carry the
  anchors, so a part needs no rails picked before a run. Volumes proposed by the system (VOL-1) come later.

### 4.4 The resolver

The resolver reads the part model and the process profile. From a recipe it computes each member's:
- `a`, `b` and `hosts` (the CAD faces of this digest);
- pull direction;
- caps: the plane in the middle of the wall's metal (`S/rules/attach.py`);
- base, sink and extension.

**What it returns:**
- the `MemberSpec`s, or
- a typed refusal: the region is missing, `s` lies outside where an end may grip, the floor is too thin to sink
  into.

**Purity.** It is a pure function of (recipe, part model, profile), so the same inputs always give the same
members. It is tested on its inverse: every member the library holds today, exported as a recipe and resolved
again, gives the same `MemberSpec` (S1).

### 4.5 Judged on demand, the library a cache

- **On demand.** A written member is judged when it is written: FAST in milliseconds to seconds, then EXACT in
  seconds, then built. It is not judged in a 1.5 h batch before the run.
- **The cache.** Every judgement is kept under the member's hash, so the library becomes a cache of members
  already judged rather than the boundary of the design space.
- **Pair rules** (spacing, crossings, junctions) are judged between the members of a recipe. CP-SAT repairs a
  set that breaks them, as it does today, keeping the most members legal.

### 4.6 Physics proposes candidates

Today topology chooses among the menu's members. Instead:
- **The field.** The cube model (10 mm, HEX8, with adjoint sensitivities: `S/generate/paths.py`,
  `S/loop/worth.py`) gives a field over the design volume's air: how much the goal gains from metal at each cube.
- **The candidates.**
  - A generator lays candidate recipes along the field's ridges, between regions where an end may grip: the
    "ridges to ribs" idea of 18 September (`docs/archive/pages/2026-09-18-ridges-to-ribs.html`), now ending in
    recipes.
  - The agent may write members from its own reading too: "tie the main-bearing boss to the left supports".
- **One judge.** Every candidate is judged by the same path in section 4.5.

### 4.7 The agent's tools

The new tools are an MCP server with typed inputs and outputs. The schema of `recipe.*` *is* the recipe
format. The current CLI stays for the menu arm.

| Tool | Answers |
|---|---|
| `part.describe` | the regions with their descriptors; the features; the loads and supports |
| `part.characterize` | where the part bends and why; the seats' condensed compliance and each load component's share of the goal (S3) |
| `part.where_metal_helps` | the field, as pictures and numbers, and candidate recipes laid on it |
| `recipe.validate` | the schema, the resolver, then FAST rules: per member, PASS or the rule and the place |
| `recipe.check` | the EXACT rules, the pair rules and CP-SAT's repair |
| `design.estimate` | the cube model's measures, by the best design's own FE ratio, with how far that ratio has erred this run |
| `design.solve` | build, mesh, FE (asynchronous); typed failures |
| `design.look` | pictures of a solved design, as today |
| `run.state`, `run.reflect` | as today |

### 4.8 Records and tokens

- **The record.** Every design keeps:
  - its recipe;
  - its resolved members;
  - its manifest;
  - its FE results: measures, the 4,096-point field, and nodal displacement and stress;
  - the decision that made it;
  - its verdict, with refusals kept beside passes.
- **The tokens.** Each member is written also as a fixed-length row:
  - its kind;
  - each end's descriptor - its position in the part's frame (scaled by the part's size), the host's normal and
    kind, the metal behind it, the distance to the nearest load and support;
  - its path, heights, thickness, draft and flange.

  A design is a set of such rows, plus a short row for the part. Because the rows name geometry rather than
  ids, the same columns mean the same thing on every part. This is what makes the data learnable across parts.

### 4.9 Reused, extended, new

| | Pieces |
|---|---|
| **Reused as is** | part model, geometry context, `MemberSpec`, member solid, the rules FAST and EXACT, design volumes, CP-SAT, cube model and adjoint, fuse, mesher, cuDSS, lineage, the harness |
| **Extended** | records (recipe, tokens), goals (several load cases, S4), `pipeline/library.py` (a candidate generator and a cache) |
| **New** | recipe schema; host regions and their ids; resolver and its inverse; judging on demand; the candidates from the field; the MCP tools; words → goal; `characterize`; the tokenizer |

## 5. The plan, stage by stage

Each stage leaves the product working end to end and ends on a measured result, as part-model.md's migration
does. Each stage gets its own implementation plan, with tasks and tests, when it starts; S0 and S1 come first.
Days are estimates of working days with Claude writing most of the code; the engineer reviews the physics and
the results.

### S0 - Foundations (2-3 days)

- Bring the agenticCAE mesher file into the repository; check that a fresh clone meshes.
- Track a curated test suite and add CI. Tests include:
  - cuDSS against Code_Aster on today's deck and on two design meshes;
  - a resolver round trip, once it exists.
- Repeatable runs:
  - CP-SAT with one worker in campaigns too;
  - a dataset refuses a dirty tree;
  - the manifest records the settings, not only their digests.
- Correct the claims as listed in the audit (section 5 there).
- Put the current work on `main` and make it the default branch; rewrite the README.

**Done when:**
- a clean clone runs the tests and one design end to end;
- two runs from one config give the same designs.

### S1 - Recipe v1 and parity on the housing (5-7 days)

- Recipe schema; host regions with ids and descriptors in the part model; the resolver; the exporter (MemberSpec
  → recipe).
- Every one of the 673 library members exported and resolved again.
- Designs 04 (`opt-20261002-073129`) and 08 (`opt-20261002-053852`) rebuilt from their recipes, meshed and
  solved.

**Done when:**
- all 673 members give back the same `MemberSpec` (points within 1e-6 mm) and the same rule verdicts;
- both designs give the same solid (volume within 1e-6) and the same FE results.

**What this proves.** The recipe loses nothing the menu had.

### S2 - The agent writes recipes on the housing (8-12 days, and about three nights of runs)

- Judging on demand, with the cache.
- The field and the candidates laid on it.
- The MCP tools.
- The brief for the recipe agent.
- **A controlled benchmark.**
  - Code frozen at one commit; the same checks for every arm.
  - Two goals: production's limits, and 20 % less metal.
  - Three arms: the menu agent, the recipe agent, the fixed workflow.
  - Three repeats each.
  - Reported: the median and the spread of solves to the goal, and the share of the goal at the end.

**Done when:**
- the recipe agent's median is no worse than the menu agent's on both goals;
- at least one design meeting a goal holds a member the menu never held: each of its ends lies more than 50 mm
  from the matching end of every library member.

**What this proves.** Writing beats or matches picking, and finds what the menu did not hold.

### S3 - Words to a goal, and the physics first (3-4 days, alongside S2)

- **Words → goal (AGT-12).**
  - The requirement in words becomes the goal and the allowed volumes, and the agent asks about what is open.
  - Judged on 10-20 briefs written by the engineer.
- **`part.characterize`.**
  - The bearing seats' compliance, condensed from 36 unit cases on one factor through the existing `components`
    solve (`S/simulate/solve.py:256-531`).
  - Checked: symmetric to round-off, and ½fᵀFf equal to the FE's work.
  - It reports each load component's share of the goal, so the agent says what governs the goal before its
    first move.

**Done when:**
- the engineer accepts at least 8 of 10 goals unchanged, and the questions asked match what was really open;
- the compliance passes both checks.

### S4 - The bracket (6-9 days)

The details are in section 6.

**Done when:**
- from the bracket's CAD, deck, process profile and goal, the recipe agent gives rule-valid, FE-proven designs that
  meet the goal, within one working day of setup;
- no file under `src/` names the bracket - the difference is data only.

### S5 - Data and first models across both parts (5-7 days, and runs overnight)

- A frozen pipeline makes a dataset of each part: recipes, tokens, results, refusals, decisions, split by run.
- A first fast model, the "checker": tokens → the FE measures, with a confidence.
- It is compared against the cube model's screen on held-out designs: rank correlation, and how many of FE's best
  it keeps in its top few.
- **The cross-part test:** trained on the housing, scored on the bracket with no bracket data, then with a few
  bracket designs.

**Done when:** the scores are recorded, whichever way they fall. "The physics screen beats the learned one here"
is a valid result.

### Timeline

| Stage | Days | Can overlap |
|---|---|---|
| S0 Foundations | 2-3 | - |
| S1 Recipe v1, parity | 5-7 | - |
| S2 The agent writes recipes | 8-12 + runs | S3 |
| S3 Words, characterize | 3-4 | S2 |
| S4 The bracket | 6-9 | S5's pipeline work |
| S5 Data and first models | 5-7 + runs | - |
| **Total** | **about 6-8 weeks** | |

**Machine time.** S2's benchmark is 18 runs of 1-4 hours. Runs go under `tools/analysis/away_only.py` and
`heavy_guard.py`, one heavy job at a time.

## 6. The bracket in detail

### The problem

- **The loads: the GE jet engine bracket challenge** (GrabCAD, 2013), the problem behind SimJEB (381 designs,
  CC-BY-4.0).
  - Interface 1: a clevis pin of 3/4 inch, loaded.
  - Interfaces 2-5: four bolts, fixed.
- **Four load cases, each alone:**

  | Case | Load |
  |---|---|
  | 1 | 35,586 N vertical |
  | 2 | 37,810 N horizontal |
  | 3 | 42,258 N at 42° from vertical |
  | 4 | 564,924 N·mm of torsion about the pin's axis |

- **The original:** titanium, Ti-6Al-4V (yield 903 MPa), made by DMLS, mass minimised at a safety factor of 1.5
  on yield.
- *Read from a secondary source* (a public reconstruction's README). The official page refused access. To be
  confirmed against the SimJEB paper before use.

### What we build for it - data only

1. **Its own bare bracket, as CAD made by code.**
   - A base plate carrying the four bolt bosses, the clevis lugs with the pin bore, and the least metal that joins
     them.
   - Our own geometry, so free to publish. The interfaces and load cases are cited from the challenge.
2. **Its deck:** the bolts fixed, the pin's load spread by RBE3, the four cases.
   - Written as a Code_Aster deck, so the existing reader and the Code_Aster cross-check apply.
   - Multiple load cases: the goal grows to "every case", and the solve to one factor with four right-hand sides.
3. **Its process profile.**
   - The same rules, other values: draft, least thickness, clearance, fillet radii, height ratio, spacing.
   - The housing's sand-casting values (members 15-25 mm, 20 mm sand) are sized for a 1-2 m housing, not for a
     190 mm bracket.
4. **Its design volume:** the challenge's envelope less the keep-outs (each bolt's tool space, the pin bore's
   clearance). Its pull is square to the base plate.
5. **Its goal.**
   - **v1:** the pin's displacement under each case no more than a limit, and the least metal.
   - **v2:** a safety factor of 1.5 on yield in every case, once a mesh-refinement study on two designs shows the
     peak stress at the rolled-on fillets converged within 5 %.

**What the members are.** Webs and gussets standing on the base plate between the lugs and the bolt bosses, and
plates between the lugs. Today's four families serve, and a family the bracket needs is a finding to record, not
a hack.

**Feasibility first.** The whole envelope, as one solid in the chosen material, solved under the four cases,
must meet v1. If it does not, the loads are scaled and the scale is stated.

**Before S4 starts:** confirm the challenge's interfaces, envelope and loads from the SimJEB paper; source the
profile's values from a cited design guide; source the material from a cited datasheet.

## 7. Risks

| Risk | How it is handled |
|---|---|
| A member written anywhere fails to build or fuse. This is why the library exists | FAST then EXACT before any build; a failure comes back as a refusal with its rule and place; the cache keeps every judgement; the menu stays as a fallback arm |
| The agent writes poor numbers (regions, `s`) | `near` and `part.describe` let it name features, not coordinates; the schema bounds every number; `recipe.validate` answers in seconds |
| On-demand judging is too slow | Measured in S2: a member judged in seconds; the cache; if it is slower, a nightly cache of likely members |
| Benchmark spread hides the difference | Three repeats, the spread reported, one commit, the same checks: the lessons of the audit |
| The bracket is infeasible in the chosen material | The feasibility check comes first, then loads scaled and stated |
| Stress at fillets not converged | Goal v1 is stiffness; v2 waits for the refinement study |
| Memory (9.5-13 GB meshes) and blue screens | One heavy job at a time; the guards; cloud runs later |
| GRC results cannot be shown | NLR's written OK (PRD-2) asked for now; until then the bracket is the public showcase |

## 8. Decisions for the engineer

| # | Decision | Recommended |
|---|---|---|
| D1 | The bracket's process and material | **Investment-cast Ti-6Al-4V**: faithful to the challenge's loads, a real aerospace process, a new profile for the same rules. Alternative: die-cast aluminium with scaled loads (MEKINT's die-casting interest; loses comparability) |
| D2 | The bracket's goal | v1 stiffness and metal; v2 the safety factor after the refinement study |
| D3 | Where the work lives | In fastcae, as feature **REC** with its PBIs, branch per PBI, as CLAUDE.md says |
| D4 | Design volumes | Kept, as where metal may go; anchors no longer need their rails; volumes proposed by the system later |
| D5 | The new tools as MCP | Yes, from the start; the old CLI stays for the menu arm |
| D6 | The benchmark's size | 2 goals × 3 arms × 3 repeats on the housing; the bracket's later |

## 9. How this serves the MEKINT application

| Their post | This plan |
|---|---|
| "synthetic geometry generation through automated CAD operations" | S1, S2: members written as recipes and built on demand, on any part |
| "embedding-friendly representations for neural network training" | S1, S5: recipes and tokens, the same on every part |
| "modular tool interfaces and execution protocols" | S2: the MCP tools, typed, with refusals that name the rule |
| "translate imagination into real-world designs by autonomously characterizing physical elements and governing principles" | S3: words → goal; the seats' condensed compliance (a true reduced-order model) |
| Generality | S4: a second part with nothing written for it |

**When to apply.** After S0 (2-3 days), with a one-page summary of this plan. Then S1, S2 and S4 each go as a
short update.

## Sources

- fastcae: `docs/member-and-geometry.md`, `docs/part-model.md`, `docs/data-engine-plan.md`, `CLAUDE.md`, and the
  code paths cited above, all read 4-5 October 2026.
- The audit: [2026-10-04-fastcae-audit-for-mekint.md](../../research/2026-10-04-fastcae-audit-for-mekint.md).
- SimJEB: Whalen, Beyene and Mueller, "SimJEB: Simulated Jet Engine Bracket Dataset",
  [arXiv:2105.03534](https://arxiv.org/abs/2105.03534) - 381 designs, CC-BY-4.0.
- The challenge's load cases and material, read from a public reconstruction's README:
  [Krishna-Ram9/GE-Jet-Engine-bracket-topology-optimization](https://github.com/Krishna-Ram9/GE-Jet-Engine-bracket-topology-optimization)
  (secondary source; to confirm).
- The challenge page, which refused access on 5 October 2026:
  [grabcad.com/challenges/ge-jet-engine-bracket-challenge](https://grabcad.com/challenges/ge-jet-engine-bracket-challenge).
