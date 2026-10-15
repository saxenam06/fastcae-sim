# fastcae's rules for clean ribs

Read from fastcae at the tag `fastcae-v1` (commit 6719dc2, 7 October 2026) on 9 October 2026.

**Where it was read.** Every path below is in `C:\Work\fastcae` at the tag
(`git -C ../fastcae show fastcae-v1:<path>`), and every line number is the tag's. The project's own
rule overrides were kept in `results/<project>/rules.json`, which is untracked data and was not
read. The values in force are taken from the ribs feature page, which quotes them
(`docs/features/ribs/status.md:52-63`). No fastcae code was run.

**How fastcae held a rule.**
- **One record of values.** The `Rules` dataclass holds the defaults
  (`src/fastcae/generate/rules.py:32-150`). Every stage reads it through `rules.now()`, and every
  campaign writes the rules it ran under (`rules.py:11-17`). Values that follow from others are
  computed in one place (`rules.py:152-213`).
- **One judge, on the CAD.** `src/fastcae/rules/member.py` reads every rule on one rib. It reads
  `FAST` on the part's 0.05 mm tessellation on the GPU, and `EXACT` on the B-rep with
  OpenCascade. Every refusal names its rule and the point that decided it
  (`docs/rules-by-stage.md:16-24`; `src/fastcae/rules/result.py:24-64`).
- **The stages.** The pattern lays only what keeps a rule: the gate `fins.placeable`, the wall scan
  `generate/screening.py` and the height cap `fins.capped`. A fast gate reads every candidate with
  the judge's own rules. Placement judges each candidate once, exactly, and fuses it alone with the
  part. CP-SAT decides the pair and pocket rules. The build fuses and checks. The mesher rolls the
  fillets on (`src/fastcae/generate/rules.py:334-400`; `docs/rules-by-stage.md:45-80`).
- **Margins.** The optimisers held every rule 1 % inside it (`inside_share`, `rules.py:137-141`)
  and every millimetre rule 0.25 mm inside (`src/fastcae/rules/method.py:17-19`). The judges read
  each rule exactly.

**Kinds** used below:
- **layer**: the pattern, the wall scan or the height cap lays only what keeps the rule;
- **CAD check**: the exact judge at placement (`rules/member.py`);
- **CP-SAT**: a constraint of the sampler;
- **build**: how the solid is drawn and fused, and the build stage's checks;
- **mesher**: a setting of the face-by-face mesher or the fillet roller;
- **dropped**: tried and taken out;
- **proposed**: written down, never enforced.

---

## In short: fastcae's answer to each of our four faults

| Our fault in `grammar.py` | fastcae's rules |
|---|---|
| **Ribs stand proud of bosses and bores** | Each end's top stands at least `flush_mm` under the top of the wall or boss it grips: 3 mm by default, **10 mm in force** from 29 September, so the root fillet has wall to roll on. The top's curve, carried on 30 mm past each end into the wall, must stay under that top too. The wall must stand at least `least_end_mm + flush_mm` (30 mm in force) over the end's bottom. The middle stays 20 mm under any metal overhead. The top never sags below its lower end. The height is at most 5 × the thickness. |
| **Shallow or near-tangent meetings** | An end meets its wall at `arrive_deg` or steeper, measured on the wall's exact face along the end's middle line: 60° by default, **45° in force**. A fan leans at most 90° − that angle from radial. A wedge between a rib's face and metal is a slot if it opens under 30°. A line grazing a face (cosine under 0.05) does not count as meeting it. A ring is closed by 4 chords, not 5 or 6 (36° and 30°). |
| **Crossings that leave specks** | Two ribs cross only at 60° or steeper, and only in the middle third of both. Their ends stand at least 45 mm apart. Any pocket of sand three ribs close, or two ribs and a wall, is at least 55 mm across. Two ribs from one root open at 60° where their fillets would meet. All of these are CP-SAT pair and triple constraints, read when the library is built. |
| **No fillets on rib tops** | Every free edge of a rib, its top included, is rounded at 5 mm, and every root is filleted at 10 mm. These were rolled onto the mesh by one rolling-ball rule, never built in the CAD: OpenCascade's fillets on fused rib seams built 0 of 42. The rules leave the fillets room: a rib at least 20 mm tall (2 × the root fillet), faces 20 mm clear of other metal (2 × the root fillet), and a tip at least 10 mm wide after draft. |

---

## 1. Rib height

### 1.1 The tallest: five times its own thickness, and under the metal it meets

- **Rule.** A rib stands at most `tallest_ratio` × its own thickness. It never stands above the top
  of the wall or boss each end grips, the volume's band, or space kept clear, whichever is lowest.
- **Value.** 5 × thickness: 125 mm at 25 mm, 75 mm at 15 mm.
- **Where.**
  - The rule: `src/fastcae/generate/rules.py:44-47`: *"never above the top of the wall or boss
    each end grips, the volume's band or space kept clear, whichever is lowest. Production's rib
    pieces stand 118-163 mm along the pull."*
  - Laid by `fins.capped` (`src/fastcae/generate/fins.py:736-747`).
  - Judged by `form` (`src/fastcae/rules/member.py:1234-1238`).
  - CP-SAT takes no thickness the height forbids. A member's thinnest cast thickness is
    `max(thinnest_mm, tallest height / 5)`, raised to a cast step
    (`src/fastcae/pipeline/library.py:95-108`).
- **Kind.** Layer, CAD check and CP-SAT.
- **Prevents.** A plate too slender for its thickness. The record gives no reason beyond
  production's own proportions.
- **Evidence.** The cap was once read against the laid thickness, not the rib's own: 9 refusals
  in the 25 September rebuild (`docs/research/2026-09-26-issue-catalogue.md:18`).

### 1.2 An end never stands above the wall or boss it grips (the flush rule)

- **Rule.** At each end, the top stands at least `flush_mm` under the top of the wall the end
  grips. Where the rib hangs, its base stands at least `flush_mm` over that wall's bottom.
- **Value.** 3 mm by default (`rules.py:54-55`: *"so the two tops never lie flush"*). **10 mm in
  force from 29 September**. That is the root fillet's radius, *"so the root fillet has wall to
  roll on, as production's do"* (`docs/features/ribs/status.md:59`, `:113`).
- **Where.**
  - Laid by the height cap (`fins.py:748-776`). Each end's height is at most the grip's top, less
    the flush rule, less the end's datum. The grip is what the wall scan read across the end's
    faces (`screening.py:149-150`; `fins._grip_top`, `fins.py:1009-1016`). The code's own reason
    is at `fins.py:748-753`: *"read that way, the S2 ring's fins were held to the 10 mm of air
    under a boss's flank and came out 30 mm tall against a boss of 60."*
  - Judged by `_footprint` (`rules/member.py:538-600`). Three lines along the rib, `flush_mm`
    over the end's top edge, must still meet the wall before the end's cap. Under the bottom edge
    too, where the rib hangs (`:557-576`).
  - Exception: an inverted T-section's flange may sit flush on its walls' lower edges (the
    engineer, 2 October 23:59; `rules/member.py:561-564`; `member/spec.py:128-131`).
- **Derived.** The wall an end grips must stand `wall_least_mm = least_end_mm + flush_mm` over the
  end's bottom: 23 mm at the defaults, 30 mm in force (`rules.py:184-188`). Below that, no end is
  offered (`screening.py:158-164`; `fins.py:2216-2227`).
- **Kind.** Layer and CAD check.
- **Prevents.** Two tops lying flush, a step that leaves a sliver along the wall's edge, and a root
  fillet with no wall to roll on.
- **Evidence.**
  - In campaign `20260929-021900`, 642 of 1,242 rib tops stopped within 10 mm of their wall's
    edge (`status.md:113`).
  - Production's five S2 ribs meet the bore boss from its lower edge, blended in. Four stand 3-5 mm
    over its top, a step down onto it; one stops 27 mm under it with a full fillet
    (`status.md:12`).
  - Pits in the mesh at rib ends were no commoner where the fillet lacked room. They came at 11 %
    of the ends whose wall has an edge within 10 mm over the top, and at 13 % of those with none
    within 15 mm (`docs/features/simulate/status.md:56`).

### 1.3 The top carried past each end stays under the wall

- **Rule.** A glued end runs on into its wall. The top's quadratic is carried past each end as far
  as the end runs on. There it must stay under what the end grips and over the member's own base.
- **Value.** `PAST_END_MM = BACK_MM + GLUE_MM` = 20 + 10 = 30 mm (`fins.py:814-816`).
- **Where.** `fins.py:783-804`: *"a top rising into its wall is lowered at that end by what it
  would gain, and a top falling towards it - an arch over a short run - raised at that end, or,
  where its cap will not allow that, the arch's middle lowered."*
- **Kind.** Layer.
- **Prevents.** A top that is under the wall at the anchor but rises proud of it inside the wall,
  where the trim then leaves a step.

### 1.4 The middle stays under the roof, read across the whole width

- **Rule.** Each station's height is capped by the room over it, read under the rib's middle and
  under each face.
  - Space kept clear caps the rib everywhere.
  - The volume's air caps it only more than an end zone from the ends: within the end zone, the
    metal over an end is what it joins.
  - Under metal overhead, the top stands the clearance under it.
- **Value.**
  - Five reads across the rib, at -1, -0.5, 0, 0.5 and 1 × its half thickness (`ACROSS_READS`,
    `fins.py:1086`).
  - 20 mm under metal overhead (`graze_mm`); `flush_mm` under the volume's own top
    (`fins.py:738-747`).
  - The gate refuses a line whose room off its end zones is under `least_end_mm + graze_mm` under
    metal, or `least_end_mm + flush_mm` under the volume's top (`fins.py:2145-2166`).
- **Where.** `roof_across` (`fins.py:1122-1158`). The whole top is held under the room, not only
  its three stations: where the curve between them rises past it, all three come down together
  (`fins.py:805-810`).
- **Kind.** Layer.
- **Prevents.** Thin slabs of sand over a rib's top, and tops cutting into tool spaces beside the
  middle line.
- **Evidence.**
  - `fins.py:1134-1137`: *"Read under the middle alone, members of the first ground structure ran
    into hole tools a few millimetres to one side; read by the air alone at the ends, the S2 ring's
    members were held to the air under the bore boss's flank, 8 mm at the ends (2026-09-24)."*
  - Rib #26 of the 27 September check stood 12.2 mm under a ceiling. The cause was a laying
    mistake: *"The layer holds a rib's top only 3 mm under metal overhead, not 20 mm"*
    (`docs/archive/pages/2026-09-27-rib-check/rib-check.html:485-493`). The fix: *"the top 20 mm
    under metal overhead, or 3 mm only where an end meets its wall's top"* (`rib-check.html:585`).

### 1.5 No sag in the middle

- **Rule.** The middle height station is never under the lower end.
- **Where.** `fins.py:777-782`: *"A top edge that runs from one wall to the other at a slope is an
  ordinary rib, however steep. One that dips in between and climbs back is not: the run pulls away
  from the metal either side of the dip and its end faces stand in the open."*
- **Kind.** Layer.
- **Prevents.** End faces left standing in the open.

### 1.6 The least height: twice the root fillet

- **Rule.** An end stands at least `least_end_mm` tall, and so does every station.
- **Value.** 20 mm (`rules.py:48-53`): *"twice the root fillet ... so the fillet on each face of
  it takes no more than half its height. Lower, the fillets laid on a design's mesh met over its
  top and turned over there (the engineer's decision, 2026-09-27; 8 mm before - what the build
  showed fuses cleanly)."*
- **Where.**
  - Judged by `form` (`rules/member.py:1239-1243`).
  - The heights' lower bounds (`fins.py:1794-1806`) and the height cap's floor (`fins.py:775`).
  - The wall scan refuses a station where the wall stands under it (`screening.py:158-164`).
- **Kind.** Layer and CAD check.
- **Prevents.** The two root fillets meeting over a low rib's top, and the mesh turning over there.

### 1.7 The base: on its floor everywhere, or hanging clear

- **On a floor.**
  - The base line is fitted by a linear programme at or under the floor's top. It is read at every
    2.5 mm station under the rib's middle and both faces of the thickest member (`_floor_fit`,
    `fins.py:878-915`).
  - The glued base then sinks to meet the floor everywhere, plus `GLUE_MM` = 10 mm
    (`rules/attach.py:247-257`).
  - The judge `on_floor` refuses a base that stands off its floor anywhere: *"a step, a dip or a
    hole under it"* (`rules/member.py:612-642`).
  - A floor that rises more than `FLOOR_RISE_MM` = 8 mm under the rib is not its floor
    (`rules/method.py:31-34`).
- **Hanging.**
  - The base clears, by the flush rule, the bottom of the wall each end grips, the volume's bottom
    and the floor at the end.
  - It is then raised until it clears metal under it by `core_gap_mm` = 6 mm: *"a thinner slot of
    sand cannot be cast"* (`rules.py:100-102`; `fins.py:1034-1083`).
  - The glue seat lifts each end only as far as the stations near it ask, by a linear programme:
    a line lifted whole would lift an end its wall already holds low (`rules/attach.py:82-155`).
- **Kind.** Layer and CAD check.
- **Prevents.** A base hovering over a step or a dip, a base cut through a thin floor, and a thin
  slot of sand under a hanging rib.
- **Evidence.**
  - An 8 mm sink datum once read ribs 8 mm too tall.
  - Bases hovered over steps, went through thin or chamfered floors, or sat 2.9 mm deep where the
    floor dips.
  - Hanging ring ribs stood 0.1-0.7 mm over metal near an end.
  - (`docs/research/2026-09-26-issue-catalogue.md:73-87`)

### 1.8 Height rules tried and dropped

- **The boss cover** (`boss_cover` 0.8, `ROOT_SHARE`):
  - *"An end on the boss a volume grows from covers at least this share of the boss's height
    there: a rib over a sliver of a boss stiffens nothing"* (`git show 4a5130e`, `rules.py:62-64`;
    `docs/archive/rib-optimisation-plan.md:371-379`).
  - Dropped by the engineer on 24 September (`issue-catalogue.md:103`) and taken out of the record
    on 26 September (commit 8664387).
- **The root window** (21 September):
  - Each end was a rectangle sunk into the heights where the wall is solid across the rib's
    thickness. Over the last 25 mm the base rose and the top fell into that window, 4 mm inside it.
  - Clean fusions went from 13 of 29 to 16 of 25.
  - A window kept 3 mm clear of every B-rep edge *"refused most fins and left the faces where they
    were, so it is built but not used"* (`docs/archive/rib-optimisation-plan.md:260-271`).
  - Superseded by plain ends that are glued and trimmed.
- **The 18 September height sheet** (a plan): *"A rib may rise to the boss it braces, never proud
  of it. Away from any feature the cap falls to three wall thicknesses"*
  (`docs/archive/pages/2026-09-18-where-ribs-may-grow.html:252-261`). Superseded by the volume's
  roof and the grip's top.
- **Height read from the air beside the rail** (21 September). At a boss's flank that air is a
  sliver, *"so every fin came out 15 to 35 mm tall and kissed the boss's edge"*. Fixed by reading
  *"the height of the metal it roots in"* (`rib-optimisation-plan.md:371-379`).

---

## 2. How a rib ends

### 2.1 Ends only on walls

- **Rule.** A member's two ends sit on rails: stretches of the volume's boundary backed by metal
  all the way along (`fins.py:306-315`). A rail must be at least 60 mm long (`fins.py:401-433`).
- **Rule.** *"Rings, sunbursts, contours and flange gussets end on another member or in the air,
  which a member - two ends on the part's walls - does not yet"* (`fins.py:2337-2341`;
  `docs/features/ribs/designs.md:165-166`). No rib ever ended on another rib. Two ribs met only
  by crossing (section 3).
- **Rule.** An end whose middle line meets no wall from outside is refused (`rules/member.py:417-428`).
- **Kind.** Layer and CAD check.
- **Prevents.** Ends floating in air, and T-junctions fastcae had no rule for.

### 2.2 The arrival angle

- **Rule.** The line through the middle of the end's face, along the rib's own end tangent, meets
  its wall at `arrive_deg` or steeper. The angle is measured on the wall's exact face, so a wall
  that leans takes the angle down.
- **Value.** 60° by default (`rules.py:56-63`); **45° in force from 27 September**, *"as two of
  production's ends are"* (`status.md:59`, `:119`).
- **Why 60°.** `rules.py:57-60`: *"so the root fillet in the sharp side of the corner stands off it
  no more than its own radius - r / sin(half the angle) - r - where at 45 degrees it stood 16 mm
  off and the fillets laid on a design's mesh turned over there."* For R = 10 mm that is 16.1 mm at
  45° and 10.0 mm at 60°.
- **Where.**
  - Measure: `arrival_deg` (`src/fastcae/part/walls.py:49-54`).
  - Judge: `end` (`rules/member.py:430-440`).
  - Gate: `placeable` (`fins.py:2167-2181`). Wall scan: `wall_glued` (`generate/curved.py:303-308`).
  - The optimisers held it with slopes: `leaving` (`fins.py:1208-1271`). Its reason
    (`:1219-1222`): *"A rib meeting its wall head-on buries its end face entirely in the metal; one
    arriving along the wall cannot, however deep it is buried: part of its end face stays in the
    open."*
  - The fast gate lets a reading through within 1° of the rule; the exact check decides there
    (`FAST_SLACK`, `pipeline/library.py:379-383`).
- **How the patterns keep it.**
  - A seed is bent only as far as it must be to leave each wall at the angle, plus 1 %
    (`_bend_to_arrive`, `fins.py:2296-2334`).
  - A fan leans at most `lean_most_deg` = 90 − arrival from radial: 30° by default, 45° in force
    (`rules.py:199-203`; `fins.py:2489-2490`).
  - A ring is closed by `RING_SIDES` = 4 chords (`fins.py:2064-2068`): *"A chord between two feet
    on the wall meets it at half the angle it spans: between neighbouring feet that is a few
    degrees - a rib lying along the wall ... Four sides span a quarter of the wall each and meet it
    at 45 degrees; five meet it at 36, six at 30 - refused."*
  - Aimed lines leave a wall within ±25° of square, in 5° steps, and are kept only where both ends
    keep the angle (`fins.py:2673-2676`, `:2759-2830`).
- **Grazing does not count as meeting.** A line meets a face only when it heads into it with a
  cosine of at least 0.05 (`FACES_THE_LINE`, `rules/method.py:35-37`; `part/walls.py:22-24`).
- **Kind.** Layer and CAD check.
- **Prevents.** An end face left in the open, a knife-edge wedge of sand in the acute corner
  (*"A shallow arrival leaves a knife-edge of sand"*,
  `docs/archive/pages/2026-09-26-rib-rules-review.html:763`), fillets standing far off the corner
  and turning the mesh over, and small faces.
- **Evidence.**
  - New faces under 5 mm² at rib ends, by arrival angle: 10 % of the ends arriving at 45-55°,
    6.5 % at 55-70°, 0.7 % at 70-90° (19 of 515 ends; `status.md:12`).
  - Rolled fillets succeeded on 0 of 3 designs at 45° and 2 of 4 at 60°, before the
    smaller-fillet fallback (`docs/archive/pages/2026-09-26-glue-rulebook.html:407`, `:727`).
  - 14 ribs were refused at 44° against 45° because the plan read a leaning face. Fixed by one
    exact reading on the face.
  - The rule went 85° → 45° (24 September) → 60° (26 September) → 45° in force (27 September).
    Fans leaning at 60° made 44 of them glance off the wall, and the ground structure fell from 77
    to 43 (`issue-catalogue.md:36-41`).
  - Production's ends meet their walls at 75-90°, but for three at 60-67° and two at 46° and 48°
    (`status.md:71`). That is why 45° was put in force (`docs/features/analysis-tools/catalogue.md:24`).

### 2.3 One wall across the end's face, and not on a round

- **One wall.**
  - Rule: three lines along the rib, across the end's face at mid-height, each meet a wall from
    outside. No round, hole or edge may lie under the end (`one_wall`, `rules/member.py:538-556`,
    `:578-589`).
  - The wall scan reads the wall's low and high on the end's middle and on the faces of every
    cast thickness (`screening.across`, `generate/screening.py:31-36`). It joins the wall's faces
    where they meet. Where the wall's heights at those offsets overlap by less than 1 mm, it
    refuses: *"a round, a step or a corner lies under the end"* (`generate/curved.py:185-257`).
- **What a wall is** (`part/walls.py:109-139`; `geometry/exact.py:133-171`):
  - a plane or a free-form face;
  - a cylinder or cone that hollows into the part, of `fillet_mm` radius or more;
  - a cylinder or cone that bulges out of the part, of `bump_mm` or more;
  - never a torus or a sphere.
- **Values.**
  - `fillet_mm`: 25 mm by default (`rules.py:64-67`); **10 mm in force from 28 September**
    (`status.md:59`, `:120`; `docs/features/input/status.md:52`).
  - `bump_mm`: 25 mm (`rules.py:68-75`): *"an end glued to it wraps over it, and the fuse and the
    mesh founder there ... on the housing every bulging round of 10-25 mm is a rounded outer edge,
    turning about 90 degrees."*
- **Kind.** Layer and CAD check.
- **Prevents.** An end draped over a round, an edge or a hole, which leaves folds and small faces.
- **Evidence.**
  - Ribs #3, #11 and #20 of the 27 September check ran along a wall instead of into it, and first
    touched an R10 fillet at a grazing 9-20°: refused (`rib-check.html:290-298`).
  - Other cases met (`issue-catalogue.md:42-49`): 15 mm tries that ended on a 10 mm corner round;
    a 12-16° crease that broke the "same wall" test; a 2.5 mm² seam sliver.
  - Production: 89 % of its ribs' glue lies on flat walls and floors, the rest touching fillets of
    5 and 10 mm and rounds of 25. Three of its 14 ends sit at a wall's corner, across two walls
    (`status.md:71`). fastcae never took an end across two walls (RIB-6 (ends at a wall's corner)
    stayed in Next, `status.md:28`).

### 2.4 The whole end glued, and drawn past the surface

- **Rule.** Every line along the rib over the end's face meets the wall from outside before the
  end's cap, so the trim leaves the whole end on the wall's own surface. The lines form the
  middle plus a 5 × 5 grid across the end's width and up its span, edges included (`whole_end`,
  `_contact`, `rules/member.py:479-535`).
- **How far an end runs on.** Each end is drawn on past its anchor until every line over its face
  has met the wall, and 10 mm more (`GLUE_MM`). The lines are cast from 20 mm back, in the rib's
  own air (`BACK_MM`) (`rules/attach.py:65-79`; `rules/method.py:20-30`).
- **Where the joint lies.** The build trims the oversized rib back to the part's surface, so the
  joint lies exactly on the part's own faces (section 7.2).
- **Kind.** CAD check and build.
- **Prevents.** An end face partly in the air.
- **Evidence.** Plates of 2 October were refused mostly by `whole_end`: an end wider than its wall
  (`status.md:69`).
- **Dropped with the glue (27 September, commit f17ef6e).**
  - The end cut 3 mm into the metal (`end_cut_mm`) and the 1 mm skin behind it (`skin_mm`).
  - The cap planes at the middle of the wall's metal (`docs/features/ribs/designs.md:50-51`).
  - The case for dropping them (`glue-rulebook.html:402-406`; `issue-catalogue.md:22-35`):
    - 38 end-cut refusals, 35 of them "stops short" on leaning or drafted walls;
    - a cut crossing the rib's middle that killed a library build;
    - 22 skin refusals;
    - thin walls broken through.

### 2.5 Where along the wall an end may sit

- **Rule.** An end stays inside the stretch of wall the scan approved, by the part of its face that
  lies past the probed face.
- **Value.** `half / sin(angle) - half + half a stride` (`end_margin_mm`, `fins.py:969-987`). By
  default it is read at the thickest member and the shallowest angle allowed. Probes run every 2nd
  rail station (`STRIDE`, `screening.py:41-42`).
- **Room in front.** A station takes an end only where a member could arrive square: 40 mm of air
  in front of the wall (`END_REACH_MM`, `curved.py:114-117`; `screening._probe`,
  `screening.py:88-109`).
- **Kept clear in front.** Nothing kept clear may stand in front of the end, over its end zone,
  across its width, from its base up to the least end height (`screening.py:170-188`).
- **Kind.** Layer.
- **Prevents.** An end sliding off the edge of its wall onto the round where two walls meet.
- **Evidence.** `fins.py:977-979`: *"ends slid to a stretch's edge met the round where two walls
  meet; held to the worst case at the gate, 88 of 246 candidates were refused that the scan had
  already read."* Ring walls held ends along only 40 % of their length, the S3 ceiling's along 70 %
  (`issue-catalogue.md:57-62`).

### 2.6 The end zone and the joint's own wall

- **Rule.** Within an end's zone, the metal over or beside the rib is the wall it joins, not a
  slot. The rib's faces may come nearer that wall than the clearance, but never other metal facing
  them.
- **Value.** `end_zone_mm = (thickest/2 + graze_mm) / sin(arrive_deg)` = 37.5 mm at the defaults
  (shown as 38 mm), 46 mm at 45° (`rules.py:190-197`).
- **The joint's wall.** It is the face the end's middle line meets, its rounds up to 2 faces away,
  and the faces the trimmed rib lies on within the zone, up to 3 faces away (`joint_faces`,
  `rules/member.py:364-394`, `:172-178`).
- **Kind.** CAD check.
- **Prevents.** False refusals at the rib's own corner fillets, while still catching true slots.
- **Evidence.** On 40 test ribs, 12 sound ribs were refused wrongly. Their wall was read as one
  CAD face, or the 20 mm as the nearest distance to any metal, or two readings of one distance
  disagreed. With the wall read as all its faces and the gap read face to face, no wrong refusal
  was left (`rib-check.html:258-261`, `:552-557`, `:572-579`).

### 2.7 Two ends never share a spot

- **Rule.** Two ribs' ends stand at least `end_gap_mm` apart, centre to centre in plan.
- **Value.** 45 mm: half of each rib and a root fillet each, 12.5 + 10 + 10 + 12.5
  (`rules.py:115-120`).
- **Where.** `choose.relations` (`src/fastcae/generate/choose.py:82-87`). A conflict pair:
  `present[i] + present[j] <= 1` (`src/fastcae/pipeline/sample.py:173-174`).
- **Kind.** CP-SAT.
- **Prevents.** Folds where two ends overlap on one wall or boss.
- **Evidence** (RIB-13 (folds where rib ends meet the part), `status.md:14`). Ends by their
  distance to the nearest other end on the same wall, over 50 designs:

  | Distance | Ends that folded |
  |---|---|
  | 0-10 mm | 58 % |
  | 10-30 mm | 22 % |
  | 30-45 mm | none of 19 |
  | 45-60 mm | none of 303 |
  | farther | 0.5 % |

  After the rule, campaign `20260929-021900` had no small face at any rib top (24 before) and 4 at
  bases (22 before).

---

## 3. Spacing

### 3.1 Between two ribs: sand each side

- **Rule.** Two ribs' centres stand at least half of each one's thickness, plus twice the sand,
  apart.
- **Value.** `sand_mm` = 27.5 mm each side, so 80 mm between centres for two ribs at 25 mm
  (`rules.py:84-86`, `:210-213`).
- **Where.**
  - Within a volume it is read on the plan, over every pair of points of two runs (`fins.spacing`,
    `fins.py:1969-2037`; `oracle.pairs`, `generate/oracle.py:21-36`).
  - Between volumes it is read in 3D, face to face, every 5 mm and again every 1 mm near the limit.
    A pair within the reading's error of the limit is a conflict (`across_volumes`,
    `pipeline/library.py:441-505`).
- **Kind.** CP-SAT.
- **Prevents.** A slab of sand too thin to cast between two ribs.
- **Evidence.** Production's rib pieces stand more than 80 mm apart (`status.md:71`).

### 3.2 Crossings: steep, and only in the middle third

- **The angle.** Two ribs crossing at `cross_deg` or steeper are a junction the foundry casts.
  Shallower, they conflict and only one stands.
  - Value: 60° (`rules.py:103-107`; `choose.py:106-112`).
- **The place.** A crossing must stand at least `cross_share` of each rib's run from either of its
  ends: the middle third.
  - Value: 1/3 (`rules.py:108-114`; `choose.py:113-116`, `:319-323`).
  - The rule's reason: *"Crossed near an end, the two ends overlap on the wall and the fuse leaves
    folds there; of campaign 20260928-051016's 49 crossings, 45 stood nearer an end than a third.
    At a half no two members cross at all - too strict for the grid patterns."*
- **Kind.** CP-SAT.
- **Prevents.** Thin wedges of sand at shallow crossings, and folds where crossing ribs' ends
  overlap.
- **Evidence and limits.**
  - No crossings at all was weighed and left: too strict for the grids. The 4 crossings in the
    middle left no fold of their own (`status.md:114`).
  - At arrival 60° and crossing 60°, no two ribs could cross in the S2 ring: all 44 of its
    crossings sat at 9-59° (`issue-catalogue.md:135`).

### 3.3 Two ribs from one root

- **Rule.** Over the first `root_free` of each run from a root two ribs share, the sand rule is not
  read: spokes converge on their boss, and two ribs meet a wall in a V.
- **But.** Where they come so near there that the root fillets would bridge their faces, they must
  open at `cross_deg` or steeper. "So near" means within half each thickness plus twice the root
  fillet. The opening is read over twice the root fillet from the root (`_narrow_root`,
  `choose.py:272-302`).
- **Value.** 35 % of the run free; 60° within 0.5 × (T1 + T2) + 20 mm (`rules.py:87-89`,
  `:103-107`).
- **Kind.** CP-SAT.
- **Prevents.** A V the fillets fill solid.
- **Evidence.**
  - A 47° V with faces 0-2.6 mm apart: the fill swallowed faces, and 352 triangles turned
    (`issue-catalogue.md:134`).
  - Spokes 20° apart on a 270 mm boss stand 94 mm apart at the boss and 134 mm a third of the way
    out (`fins.py:1939-1942`).

### 3.4 Pockets: three ribs, or two ribs and a wall

- **Rule.** Three ribs that cross two by two may not all stand if the pocket of sand they close is
  under twice the sand across. The same holds for two crossing ribs that both run on to one wall.
- **Value.** 55 mm, measured as the diameter of the largest circle in the sand left once each rib
  takes its metal (`pockets`, `choose.py:130-171`; `_walled`, `:187-223`; `_sand_across`,
  `:237-261`).
- **Where.** In CP-SAT, a triple: `present[a] + present[b] + present[c] <= 2`
  (`sample.py:175-176`). A wall pocket is a pair conflict (`choose.py:117-124`).
- **Kind.** CP-SAT.
- **Prevents.** A pocket the root fillets fill solid: a lump of metal and a speck the mesh cannot
  follow.
- **Evidence.** A triangle of three crossing ribs about 28 mm across, its inscribed radius about
  8 mm, under the fillet's 10 mm. Two ribs crossing just before the ring closed a pocket of about
  20 mm against it (`glue-rulebook.html:630-631`; `issue-catalogue.md:145-146`).

### 3.5 Plates and flanges keep their own width clear

- **Rule.** A member wider than a web (a plate, or a T-section's flange) conflicts with any member
  it comes near in plan. Near means within half of each one's footprint plus twice the sand.
  A web under a flange is the T-section, a member of its own (`plate_meets`, `choose.py:72-81`).
- **Kind.** CP-SAT.
- **Prevents.** A slot of sand under a plate, thinner than the fillet's ball.

### 3.6 A rib's faces clear of other metal

- **Rule.** 20 mm of sand stands between a rib's faces and every face of the part facing them
  within 30° of parallel. It is read face to face, straight out along the face's normal. A face
  opening wider is a corner, where the root fillet forms.
- **Values.**
  - `graze_mm` = 20 mm, twice the root fillet (`rules.py:90-94`): *"a gap narrower than the
    fillet's ball fills solid - a slot the casting cannot keep, and the mesh cannot follow (the
    engineer's decision, 2026-09-26; 8 mm before)."*
  - `slot_deg` = 30° (`rules.py:95-99`).
- **Where.**
  - `clearance` and `_gaps` (`rules/member.py:936-1046`): the points read every 2 mm, read again
    every 0.25 mm within a spacing of the limit, and the least 24 read exactly on the B-rep
    (`rules/method.py:9-16`).
  - Within an end zone, the joint's own wall is judged by the arrival angle: its top or base faces
    make a slot only where they close on the wall at under `arrive_deg` (`:1045`, `:1108-1110`).
  - A rib that runs into the part between its end zones is refused (`:973-986`). So is one the
    part's metal cuts in two (`:215-232`).
  - The gate and the optimisers hold the rib's middle line `thickest/2 + graze` = 32.5 mm from the
    metal, counted by the millimetre along the run (`fins.clearance`, `fins.py:641-692`).
- **Kind.** Layer and CAD check.
- **Prevents.** Thin slabs of sand. `rib-check.html:398`: *"It overheats and cracks, or washes
  into the casting, and the metal on either side cools slowly and turns porous."*
- **Evidence.**
  - Clearance 8 → 20 mm cut the library from 90 to 62 ribs. None of production's rib faces stands
    5-20 mm from metal facing it (`glue-rulebook.html:546`; `status.md:71`).
  - An averaged clearance once let a rib graze metal for 27 mm and pass, which is why it is counted
    by the millimetre (`fins.py:654-656`).
  - The reason for the rule (`fins.py:258-263`): *"One that runs alongside a wall at a glancing
    angle is neither in nor out: the fuse carves shallow scallops where the two surfaces graze, and
    every scallop leaves faces of a few square millimetres."*
- **Earlier reading, changed.** The 20 mm was first read as the nearest distance to any metal.
  That refused ribs passing an open corner, so it became face-to-face. The 27 September page
  proposed *"less than 60° off parallel"* (`rib-check.html:573`); the record holds 30°.

### 3.7 Kept clear: holes, bores, held faces

These are the design volume's rules, cut out of its air before anything is laid
(`rules.py:127-144`; `src/fastcae/space/volumes/keepouts.py`):

- a hole's tool, 1.8 × the hole's radius across and 3 diameters past each open end;
- past a bore and along a bearing's line, 5 mm wider than the bore;
- a register, a bore shallower than 0.1 of its diameter, which stops nothing past it;
- 8 mm in front of every flat face the deck holds or loads.

A bore or boss is read only where its faces go 100° round its axis (`CYLINDER_WRAP_DEG`,
`src/fastcae/input/features.py:42-48`): *"Slivers of a 200 mm curve at the foot of a wall, 8
degrees round, were read as 400 mm bores and kept 1.9 m of space clear."*

- **Kind.** Layer (the volume) and CAD check (`kept_clear`, `rules/member.py:1133-1172`). The
  gate reads the whole rib, over its full height (`fins.py:2189-2207`).
- **Evidence.** Five ribs stood 2-8 mm into bolt-hole tool spaces. A grid cell hid 12 fans standing
  1-3 mm in (`issue-catalogue.md:109-115`). The gate tested only the rib's lowest 8 mm
  (`rib-check.html:302-309`). Still open at the tag: *"The gate does not see tool spaces within
  15 mm of an end"* (`status.md:137`).

### 3.8 Length, bend and the curve's form

- **Length.** At least `shortest_ratio` × the laid thickness, 3 × 25 = 75 mm; at most 500 mm along
  the curve (`rules.py:79-83`, `:173-176`).
- **Bend.** No tighter than a 200 mm radius in plan: *"what a rib on a housing looks like, not a
  casting limit"* (`rules.py:76-78`). Judges read the tightest station exactly (`turn_rule`,
  `fins.py:1892-1936`; `member/spec.py:291-298`).
- **The curve's control points stay in their own halves.** The first sits between 0.15 and 0.5 of
  the chord and the second between 0.5 and 0.85, so *"a cubic ... never loops back on itself"*
  (`ALONG`, `fins.py:1161-1165`). Each sits at most 40 mm across the chord (`BAND_MOST_MM`,
  `fins.py:2073`).
- **Kind.** Layer and CAD check.
- **Prevents.** Folding ribs, hairpins and self-intersecting swept faces.
- **Evidence.**
  - Members came out of topology turning as tight as 29 mm against a rule of 200, because the bend
    was a mean charge over all members. It became a hard rule (`fins.py:1902-1905`;
    `issue-catalogue.md:17`).
  - 38 of 60 fins folded into hairpins before the control points were bounded
    (`rib-optimisation-plan.md:380-381`).

### 3.9 The set

- At most 24 members a design (`sample.py:177`).
- Each design differs from every earlier one by at least 2 members (`sample.py:190-195`).
- Its metal lies within its level of the target's (`sample.py:185-189`).
- CP-SAT runs with one search worker in the loop's roundings, so the same start gives the same
  designs (`src/fastcae/loop/relax.py:252-255`).

---

## 4. Thickness and draft

### 4.1 Thickness

- **Values.** Laid at 25 mm, sized between 15 and 25 mm, cast in 5 mm steps: 15, 20 or 25 mm
  (`rules.py:34-43`, `:157-165`).
- **In force from 28 September: 25 mm only** (`thinnest_mm` 25), so no rib is built at a thickness
  it was not checked at (`status.md:58`, `:115`).
- **Evidence** (RIB-12 (built only at the checked thickness), `status.md:13`). In campaign
  `20260928-051016`, 82 % of the ribs were built at 20 mm, and all 19 ribs the fuse dropped were
  among them. None of the 116 ribs at 25 mm or the 30 at 15 mm was dropped. Rebuilt at 25 mm, four
  failed designs fused whole.

### 4.2 Draft and the tip

- **Draft.** Each face leans in toward the top by `draft_deg` (`rules.py:145-147`): *"the
  process's figure; 1 degree until the foundry gives its own."*
  - The thickness is given at mid-height, so the base is thicker and the top thinner
    (`member/spec.py:327-334`).
- **The tip.** At least `tip_mm` wide, where the draft leaves it thinnest (`rules.py:148-150`).
  - Value: 10 mm. The tip is `T - H·tan(draft)` (`rules/member.py:1216-1217`, `:1254`).
- **A guard proposed and never enforced.** `t ≥ 2r + 2 mm` = 12 mm, so the two 5 mm edge rounds
  never meet over the top. *"With t = 2 r the two rounds would meet; at 1° draft and H ≤ 5 T the
  top is never under 13.7 mm, so today they never do"* (`rib-rules-review.html:633`;
  `glue-rulebook.html:301`, `:757`).
- **Kind.** Layer and CAD check.
- **Prevents.** A rib that will not leave the mould, and a top too thin for its rounds.
- **Production.** Production's rib flanks have zero draft, exactly parallel and vertical. Its
  drawing's only casting rule is *"ALL NON-SPECIFIED RADII R3.0 AND CHAMFERS 1X45°"*
  (`docs/archive/16-implicit-rib-variants.md:202-208`).

### 4.3 Rib against wall thickness: no rule in force

- **At the tag.** The rib-to-anchor ratio (`k_w`) *"waits for the foundry's figure"*
  (`docs/code-map.md:174`). The rulebook proposed it as *"A thick rib on a thin wall pools metal at
  the joint"* (`glue-rulebook.html:355`, `:410`; `rib-rules-review.html:796-805`).
- **The distance-field era** (mid-September, archived): rules of thumb, marked *assumed*.
  - A rib at most 0.8 of the wall it meets; a wall too thin got a pad.
  - A rib at most 0.8 of the floor it stands on (0.8 × floor + 0.5 mm on 15 September), or left
    out.
  - Thickness 0.6-1.0 of the plate it stands on.
  - Thick spots: a junction section over 2 × the wall beside it, a warning.
  - A wall no thinner than 8 mm.
  - (`docs/archive/generate.md:219-230`, `:282`, `:414`, `:450-453`;
    `docs/archive/ribs.md:510-513`)
  - Evidence: only 12 mm ribs passed on 15 mm floors (`issue-catalogue.md:100`).
- **Production.** Ribs 25 mm (rear) and 20 mm (front); *"rib ≤ wall, ideally 0.8 × wall"* was the
  repo's working rule (`16-implicit-rib-variants.md:210-211`).

### 4.4 The largest section, and the member families

- **Webs.** At most 25 mm thick.
- **Plates.** Lying across the pull: 25 mm thick along the pull, 50-120 mm wide.
- **T-sections.** A 25 mm web under an 80-120 × 25 mm flange (the engineer, 2 October;
  `status.md:107`).
- **T-section construction.**
  - The web is drawn half the flange's thickness into the flange, so no face of one lies on a face
    of the other (`INTO_FLANGE` 0.5, `member/solid.py:49-51`).
  - The flange is drawn 1 mm farther into its walls than the web (`FLANGE_PAST_MM`,
    `member/solid.py:52-54`).
  - Web and flange are fused, then checked as one valid solid (`member/solid.py:57-72`).
- **Flange tapers.** A tapered flange narrows to the web's thickness over 1 × its own width
  (`TAPER_OF_WIDTH`, `pipeline/library.py:179-191`). Each end then meets its wall only as wide as
  the web, as production's S2 flanges stop short of the bore.
- **Inverted T-sections** (production's S2 rib).
  - The web stands at least 5 mm over the flange at each end (`LEAST_WEB_MM`,
    `pipeline/library.py:225-251`).
  - The web's ends are judged as tall as the whole member (`rules/member.py:111-121`).
- **Dropped.** The sloping T-section: *"its deep web hangs off its wall under the flange, metal
  that does not stiffen"* (the engineer, 2 October 19:31; `pipeline/library.py:356-358`).
- **Not built.** A hot-spot audit of the finished part, the "certification", was planned
  (`docs/data-engine-plan.md:43`, `:134`) and never coded.
- **Production.** About two thirds of production's S2 metal is in flanged T-ribs, a 120 × 25 mm
  flange on a 17 mm web (`docs/features/ribs/families-plan.md:13-17`).

---

## 5. Fillets

### 5.1 The radii

- **Values.** Root fillet 10 mm where a rib meets the part; edge round 5 mm on a rib's own edges.
  Both are production's own figures (`rules.py:123-126`). Production's root fillets measure R5-10
  mm (`16-implicit-rib-variants.md:202`).
- **"12" is not a radius.** The mesher meshes a root fillet at 12 elements a turn, on both sides:
  - rolled onto a design (`ROOT_PER_TURN`, `src/fastcae/shape/band.py:898-903`);
  - drawn in production's CAD (`ROUNDED_PER_TURN`, `src/fastcae/simulate/face_mesh.py:272-282`).

  This was SIM-10 (rib roots meshed alike). The OPT-7 (mesh time) research documents asked for a
  "12 mm root fillet" and flagged the clash. fastcae's own reading
  (`docs/research/2026-10-06-geometry-technology-lessons.md:363-368`): *"Inferred: '12' in the
  mesher notes means 12 elements a turn, not 12 mm."* A note that says "root fillets 12 both
  sides" means 12 elements a turn, on the design and the target alike.

### 5.2 The rules that leave the fillets room

Several rules exist only so the 10 mm fillet can roll:

| Rule | Value | Why |
|---|---|---|
| Least height | 20 mm = 2 × R | the two face fillets do not meet over the top (`rules.py:48-53`) |
| Clearance | 20 mm = 2 × R | a gap narrower than the ball fills solid (`rules.py:90-94`) |
| Arrival | 60° | the fillet in the acute corner stands off no more than R (`rules.py:56-63`) |
| A V at a shared root | 60° within 2 × R | the fillets would fill it (`rules.py:103-107`) |
| Pockets | 55 mm = 2 × sand | the fillets would fill it (`choose.py:130-140`) |
| Flush | 10 mm = R | the fillet has wall to roll on (`status.md:113`) |
| Ends apart | 45 mm = T/2 + R each | each end's fillets clear of the other's (`rules.py:115-120`) |
| Tip guard (proposed) | 2r + 2 = 12 mm | the two edge rounds do not meet (`glue-rulebook.html:301`) |

### 5.3 How fastcae made them: rolled onto the mesh, never in the CAD

- **The solid stays sharp.** `src/fastcae/member/solid.py:37-41`: *"sharp: its fillets and rounds
  are rolled onto the design's mesh (fastcae.shape.band), not built into its solid."*
- **Why.** `docs/member-and-geometry.md:89-91`: *"OpenCascade's fillet on the fused part cannot
  close a fillet at a rib's end corners - on one design's 19 ribs it built one at the 10 mm root
  fillet and five at 3 mm, the same corners failing at both, and crashed on others."*
- **The method** (`src/fastcae/shape/band.py:1-28`, `:398-515`). One rolling-ball rule for every
  joint, on a 1 mm distance grid round each group of ribs:
  1. Each rib is **opened** by the edge round, shrunk by it and grown back, so every free edge
     rounds, the top's two edges included (`band.py:452-457`).
  2. The part and the ribs are **closed** by the root fillet, grown by it and shrunk back. This is
     done pair by pair: each rib with the part (`band.py:480-483`), and each two ribs whose fields
     come within the ball of each other (`band.py:484-499`).
  3. What the part's own closing fills is taken off, so the part's holes, slots and corners stay as
     its CAD has them.
  4. A fill is kept within the root fillet and 1 mm of a rib (`KEEP_MM`, `band.py:44-45`). A
     pocket three ribs enclose is filleted at its corners, not filled.
- **On the mesh.**
  - The band sizes the mesh: a root fillet at 12 elements a turn, growing 1.5 mm per mm away
    (`band.py:518-547`, `:58-60`).
  - Every node the band stands off by more than 0.05 mm is moved onto the band's surface, drawn by
    VTK's flying edges.
  - The few triangles that turn over are mended where they stand (`band.py:661-809`;
    `src/fastcae/shape/mend.py:1-10`).
  - Nodes on faces the deck acts on are never moved.
- **The fallback.** Where a fillet turns the surface over or runs it through itself, a corner too
  tight for its ball, it is rolled again there at half its radius, then a quarter (5 mm, then
  2.5 mm). Only then is the corner held sharp: 3 tries, each held back 10 mm wider (`SMALLER`,
  `SHARP_MM`, `SHARP_TRIES`, `band.py:66-79`). *"A smaller fillet stands nearer what the foundry
  casts there than none (the engineer's call, 2026-09-27)."*
- **Which crossings count.** Only crossings more than 3 mm from one the surface had before the
  fillets are blamed on them (`band.py:912-928`). This was SIM-6 (ten designs lost to one boss
  spot): *"ten designs were lost to crossings the part's own surface had, 70 mm from any rib."*
- **Kind.** Mesher.
- **Evidence.**
  - Rolled smaller, design 04 went from 15 corners left sharp to none (`simulate/status.md:64`).
  - The fillets move displacement by 1.3-1.6 %, inside what mesh sizing alone moves
    (`status.md:99`).
  - At 8 elements a turn, two elements stood across a 10 mm fillet, and stress peaks there moved
    up to 17 % from 8 to 12 a turn (`face_mesh.py:277-279`). A design with cramped rib roots read
    4.1 % off at 8 (`simulate/status.md:111`).
  - The fillet bands dominate the mesh: 4.6 min a design, peaking at 13.2 GB
    (`docs/research/2026-10-06-geometry-technology-lessons.md:61-62`).

### 5.4 Fillet routes tried and dropped

| Route | Result | Where |
|---|---|---|
| OpenCascade fillets on fused rib seams | 0 of 42, with silent crashes | `issue-catalogue.md:175`; `glue-rulebook.html:728` |
| Rib by rib on the fused solid | 1 of 19 at 10 mm, 5 of 19 at 3 mm, crashes (27 Sept) | `2026-10-06-geometry-technology-lessons.md:59-60` |
| Fillet after the fuse | failed 0 of 3 on this housing (18 Sept) | `docs/archive/pages/2026-09-18-ridges-to-ribs.html:445` |
| CAD fillets in OPT-7's trials | 5 of 17 ribs built | `docs/features/optimize/status.md:29` |
| A flared foot built into each rib, dipping a few mm into the wall (18 Sept) | superseded | `2026-09-18-ridges-to-ribs.html:399-402`, `:445` |
| Flared end fillets in the CAD | lumpy; 3 of 11 failed; six ribs left 2-6 solids (25 Sept) | `issue-catalogue.md:70` |
| Strips built into members | ruled out by the engineer (26 Sept) | `2026-10-06-geometry-technology-lessons.md:163`, `:377-378` |
| The field era's analytic blend `k = R(1 - nₐ·n_b)` | worked on a field; an end's normals taken from grid differences grew R10 to R13.7 | `docs/archive/generate.md:135-158` |
| Per-joint fillet builders | broke with each new kind of joint | `issue-catalogue.md:200` |
| Profile-first rounds, root shoes, junction templates, local R12 geometry (OPT-7 research) | proposed; parked on 1 October | `docs/opt7-fillet-research.md:98-118`; `docs/features/optimize/status.md:29` |

---

## 6. Castability

### 6.1 The pull, and what may stand across it

- **The pull is the volume's own axis.** `fins.py:1708-1711`: *"Up is the volume's own axis.
  Measured on this housing: with it, the floor under every column is metal in both volumes;
  against it, 99 % of the S3 ceiling's columns floor at the band's own edge."*
- **Webs stand along the pull.** A rib is drawn on the volume's plan, square to the pull, and stood
  up: a prism whose faces are drafted toward the pull (`member/spec.py:4-11`;
  `docs/data-engine-plan.md:54-56`).
- **Plates lie across the pull** only where the casting is open. *"The draw rule allows it where
  the casting is open (the mouldable rule ... no undercut along the pull, or a face the core
  forms)"*. Their top draws and their underside is formed by a core (the engineer, 2 October;
  `docs/features/ribs/families-plan.md:56-58`).
- **Kind.** Layer.

### 6.2 Undercuts: excluded by construction, never measured

- **Rule.** *"A zig-zag across the draw is fine; a zig-zag along it is an undercut. The rib's faces
  stay parallel to the draw or it will not leave the mould. The parameterisation enforces this by
  construction"* (`docs/archive/rib-optimisation-plan.md:85-89`, `:131-135`).
- **The mouldable rule** was written as *"its faces drafted at least; no undercut along the pull on
  the fused part"* (`docs/member-and-geometry.md:112`). Only the draft is measured in code.
- **Dropped.** An explicit check that rejected any metal along the pull from a rib's tip.
  *"Variants hold no pull direction, and a check that rejects any metal along the pull from a rib's
  tip, however far, and does not know that cores form the pockets inside a casting, rejected every
  design built on the housing"* (`docs/archive/generate.md:434-437`).
- **Kind.** Layer by construction; the explicit check was dropped.

### 6.3 The sand rules are the castability rules

What fastcae called castability is the set of sand-width rules:

- 20 mm face to face within 30° (3.6);
- 6 mm under a hanging base (1.7);
- 27.5 mm each side between ribs (3.1);
- 55 mm pockets (3.4);
- 60° at a shared root (3.3);
- the flush rule's step at a wall's top (1.2).

The rulebook put the principle as *"A gap is nothing, or at least one ball"*: sand narrower than
the root fillet's ball cannot stand. A rib too near other metal could move off to 2R, or *"move on,
until it touches, and the contact becomes one more joint"*. That second way was offered to the
engineer and not built (`glue-rulebook.html:783-784`).

### 6.4 How the check measured

- **Two readings of one rule** (`docs/member-and-geometry.md:16-21`):
  - `FAST`, on the GPU, on a 0.05 mm / 10° tessellation (`src/fastcae/geometry/context.py:22-25`);
  - `EXACT`, on the B-rep (OpenCascade's classifier and line intersector,
    `src/fastcae/geometry/exact.py:46-122`).

  The fast gate stops a candidate only past the fast reading's own error, plus 0.5 mm (1° for the
  arrival). Nearer the limit, the exact check decides (`pipeline/library.py:379-383`, `:508-563`).
- **Each point of the rib's surface has a state** (`rules/member.py:698-762`):
  - attached: what the trim takes off;
  - in transition: where its face runs into the part at the arrival angle or wider;
  - free: the rest. Only free surface is held to the clearance.
- **Placement fuses each candidate alone with the part**, as the build fuses it. One that does not
  make one valid solid is refused (`one_solid`, `pipeline/library.py:389-408`, `:683-688`).
  - Library `bc61092e9fe73832` refused 27 this way (`status.md:154`).
- **Measure once, decide once.** Nothing moves a rib after it is measured; CP-SAT alone decides
  which stand together (`status.md:116`; `docs/data-engine-plan.md:47-52`).
- **Evidence.**
  - After the reading fixes of 27 September, 27 of 40 test lines were good ribs (16 before), with
    no wrong refusal left. *"The gate stops exactly the 13 the exact check refuses"*
    (`rib-check.html:258-281`).
  - The fast and exact readings of one distance disagreed by 0.3 mm on a sloped face (19.96
    against 20.25 mm). At a joint the angle rule now decides (`rib-check.html:531-538`).
  - A floor read from a 5 mm cube grid refused 14 ribs, which led to the rule "every check on the
    CAD" (`issue-catalogue.md:80`).
  - Holding the casting rules inside topology cost 11 % on displacement and 25 % on strain energy,
    and made each step 3 × slower. They are enforced at placement instead
    (`docs/archive/pages/2026-09-25-rib-network-pipeline.html:365-369`, `:494`).

---

## 7. Slivers: what made them, and how fastcae removed them

### 7.1 Causes, cures and evidence

| What made slivers or bad meshes | Cure | Evidence |
|---|---|---|
| Outlines traced from the part's sections, or unioned with the wall's silhouette: *"The sliver is the notch"* | Geometry from parameters only, one face a piece; never traced, clipped, notched, chamfered or tapered | 7-31 stepped edges a rib; 25 of 30 plates rejected for faces under 5 mm² at the fuse; members drawn from exact pieces fused with 0 new small faces (`docs/features/ribs/design-generation.md:113-125`; `2026-10-06-geometry-technology-lessons.md:51-53`; `docs/features/ribs/next-plan.md:85-100`) |
| A rib built as a chain of flat plates | One body swept along its curve | *"built as a chain it leaves a sliver face at every lap"* (`src/fastcae/generate/cad.py:72-74`); every arc joint a sliver (`design-generation.md:109`) |
| An end face running a millimetre or two alongside a wall's edge, a floor or a ceiling; a rib grazing a wall | The arrival angle, the clearance, and the end inside its stretch of wall | Every face under 5 mm² on the curved ribs sat where an end stood above or below the wall's solid band, or where a rail ran 1-2 mm alongside a wall's top edge, floor or ceiling (`rib-optimisation-plan.md:260-263`); grazing carves scallops (`fins.py:258-263`) |
| A rib's section read too coarsely near its ends | Sections every 0.5 mm within 40 mm of each end | At 2 mm *"the rib's edge ran all but flush with the wall, and the fuse left a face under 5 mm² there - eight of them on one rib"* (`generate/curved.py:29-35`) |
| An end cut too near its closing face | Draw the end 10 mm past its cut, then cut by a half-space | Drawn 2 mm past, a cut aslant a leaning wall left a 0.8 mm³ film as a second solid; 5 or 11 mm gave one solid (`member/solid.py:28-32`) |
| An end cut as a cylinder coaxial with a round wall | Always a plane | *"a member whose end face was a cylinder round the hub's own axis fused into nothing at all"* (`part/walls.py:164-170`) |
| A member drawn straight to two tilted end planes | Draw it long and square, then cut by the half-space beyond each plane | An inverted T's plate fused with its web as two solids (`CLAUDE.md:47`) |
| Ribs drawn into walls coming out beyond them | Trim every rib back to the part's surface before the fuse; keep the piece holding its middle; report the stray | A 16 mm³ sliver broke the fuse of four designs; trimmed, all four fused whole (`member/solid.py:164-174`) |
| Sunk ends (the cut-in era) | Glued ends; small faces reported, not rejected | 2-14 corner faces under 1.5 mm² a design where a sunk end met its wall, and every one meshed with 0.04 % bad tets (`generate/build.py:139-146`) |
| A member face passing a few mm from the core's own face seams | Plane cuts and the one-wall rule | A 2.5 mm² seam sliver; a 0.5 × 100 mm strip the 5 mm² judge misses (`issue-catalogue.md:42-49`; `2026-10-06-geometry-technology-lessons.md:262-263`) |
| Two rib ends on one spot | `end_gap_mm` 45 | 58 % of ends 0-10 mm apart folded (section 2.7) |
| Crossings near an end | `cross_share` 1/3 | 45 of 49 crossings stood nearer an end than a third (section 3.2) |
| Ends on rounds, bulging rounds and tori | `fillet_mm`, `bump_mm`, no torus or sphere | section 2.3 |
| A rib built thinner than it was checked | One thickness | 19 of 19 dropped ribs were built at 20 mm (section 4.1) |
| Ribs that each fuse alone, fused one after another | All ribs in one boolean, one at a time only as the fallback | *"16 ribs that each fuse alone left 4 failing in turn, and went in whole at once in 4 s"* (`cad.py:148-151`); ribs that fuse alone can still make slivers together, which two of 20 did (`design-generation.md:184-185`) |
| The housing's own surface: gmsh fans on narrow strips, seamed faces | The mesher's repairs (section 7.4) | SIM-6: a fan of flat triangles over a 10 mm × 243 mm strip of the boss cut through three bolt holes (`simulate/status.md:22`) |
| A narrow land the fuse leaves where a rib meets a wall | Meshed again on a finer rim, then by Delaunay | *"its rim spaced wider than it is across"* (`face_mesh.py:18-22`) |

### 7.2 The build rules for a clean solid

- **The rib's faces** are ruled between its four long edges. The edges are B-splines through the
  same stations, 2 mm apart, fitted within 1 µm and sewn at 1 µm. The solid is turned outward
  (`member/solid.py:22-27`, `:75-129`, `:227-255`).
- **Each end with a cut of its own** is drawn 10 mm past its plane, then cut by the half-space
  beyond it. A cut that leaves more than one solid fails the rib (`member/solid.py:132-161`).
- **A cut that crosses the rib** anywhere but at its own end is refused. It would cut the rib in
  two (`member/spec.py:434-453`).
- **The trim.** The rib is cut by the part, and the piece holding its middle is kept. Other pieces
  are stray metal, reported with their volume (`member/solid.py:164-215`).
- **The fuse** (`generate/cad.py:124-310`):
  - one non-destructive boolean for all ribs, one at a time only where that fails;
  - coplanar pieces merged only among the faces the fuse made, so the part's own faces stay as
    they were (`_unify`, `:378-394`);
  - where BRepCheck fails: ShapeFix on the flagged faces only, on a copy; the whole shape only when
    that is not enough;
  - a retry with 1 µm of fuzz, only when BRepCheck fails (`FUZZY_MM`, `:240-245`);
  - checks: one valid solid; at least 99 % of the part's volume kept; every tool solid still held,
    six points tested inside each (`:61-66`, `:300-310`).
- **The build stage's checks** (`generate/build.py:232-264`):
  - every rib fused; one solid;
  - the metal added within 0.8-1.2 of what was planned;
  - new faces under 5 mm² counted. Campaigns ran with `small_faces="report"`, so the count is
    reported and the mesh's own checks decide (`generate/workflow.py:535`).
- **A proposed gate.** The built rib against its drawing, within 1.0 mm on centre line and top and
  0.5 mm on thickness (`next-plan.md:101-103`, `:202-203`).

### 7.3 The narrow-face measures

- **The area judge.** `least_face_mm2` is 5 mm² (`rules.py:121-122`; `build.py:93-98`). It misses
  long strips: *"a 0.5 × 100 mm strip that the <5 mm² face judge misses; a narrow-face judge is
  still open"* (`issue-catalogue.md:44`).
- **A face's width** is twice its area over its perimeter. The mesher used it to size narrow faces
  (`face_mesh._narrow_sizes`, `face_mesh.py:393-408`). A tool listed new faces narrower than 8 mm
  this way (`tools/analysis/cad_new_narrow_faces.py:2-4`, `:19`), ported but never run.
- **Knife edges.** Edges where the solid's two faces fold back within 8° of opposite, *"a metal
  wedge or an air crevice too thin to mesh"* (`tools/analysis/cad_knife_edges.py:2-4`, `:24`).
  Ported, never run.
- **On the mesh** (`src/fastcae/simulate/skin.py:1-16`):
  - a sliver is a skin triangle whose least angle is under 5°;
  - a star is a node with 14 or more triangles round it and a sliver among them;
  - a fold is two neighbouring triangles turned more than 120° apart.

### 7.4 The mesher's settings

From `src/fastcae/simulate/face_mesh.py` and `src/fastcae/generate/solve.py`:

- **Mesh.** gmsh, face by face, on shared curve nodes. TET10, filled at the surface's own sizes,
  smoothed by gmsh's and then Netgen's optimisers. Netgen took tets under quality 0.1 from 0.10 %
  to 0.04 % (`face_mesh.py:1192-1196`).
- **Sizes.**
  - 25 mm within 60 mm of the added metal and of the deck's loaded groups, 50 mm elsewhere, 4 mm
    least (`solve.py:65`; `face_mesh.py:53`).
  - A curved edge at 8 elements a full turn, never under 1 mm (`face_mesh.py:106-111`, `:216-225`).
    The engineer chose 8 over 12 on 29 September: 20 % fewer tets, inside the noise.
  - Root fillets at 12 a turn (section 5.1).
- **Narrow faces.** A face narrower than its elements has its rim divided at 3 × its width, never
  under 8 mm (`face_mesh.py:387-408`).
- **Folded faces.** A face whose own triangles fold (neighbour normals' dot under -0.5) is meshed
  again by Delaunay, at half its width, halved each round, 3 rounds (`face_mesh.py:228-235`,
  `:790-832`).
- **Fans.** A face meshed as a fan is meshed again: a triangle longer than 2 × the size, or a star
  (`face_mesh.py:340-384`).
- **Repair.**
  - Nodes within 0.1 mm made one (`face_mesh.py:113-115`).
  - Edges under 3 mm collapsed, shortest first, at most 4 nodes onto one, only where the surface
    stays one closed sheet and no triangle turns. Never within 0.3 mm of a face the deck acts on
    (`face_mesh.py:116-123`, `:963-1040`).
  - This trades about 2 kg of the housing's small fillets and holes for sound elements (accepted on
    25 September).
- **Seamed faces.** A face closed round a seam that covers under 80 % of its area is meshed opened
  along its seam (`face_mesh.py:124-127`).
- **Planar meshing.** A face meshed in its own plane is never asked for elements finer than 1 mm
  (`face_mesh.py:657-660`).
- **MeshFix** only closes what is still open (`face_mesh.py:24-32`).
  - A MeshFix patch within 5 mm of a deck face refuses the mesh (`solve.py:52-54`).
- **Crossings** are found exactly before the fill, with CGAL through libigl (`band.py:931-942`).
- **The mesh gate** (`build.py:33-34`, `:309-331`; `generate/records.py:20`):
  - at most 0.08 % of tets under quality 0.1;
  - none inverted;
  - at most 415,000 TET10.

### 7.5 Healing and tolerances

- **No healing of the design's CAD** but the fuse's own mending (7.2). A defeaturing trial took
  fillets under 3 mm and unloaded holes under 8 mm out of the part's CAD
  (`tools/analysis/cad_defeature_trial.py:1-4`). The standing rule was to defeature them only off
  the deck's faces (`2026-10-06-geometry-technology-lessons.md:161`).
- **Tolerances.**

  | What | Value | Where |
  |---|---|---|
  | On a face (classifier) | 1 µm | `exact.py:16-17` |
  | Sewing, edge fit | 1 µm | `solid.py:22-27` |
  | Fuzzy fuse retry | 1 µm | `cad.py:240-245` |
  | A point exactly asked which side of the trim | within 1 mm of the part | `rules/member.py:159-162` |
  | Trimmed piece read at | 0.1 mm | `rules/member.py:167-169` |
  | FAST tessellation | 0.05 mm, 10° | `geometry/context.py:22-25` |
  | gmsh geometry tolerance | 1e-3 | `face_mesh.py:154` |
  | The optimisers' margin | 0.25 mm, 1 % | `rules/method.py:17-19`; `rules.py:137-141` |

---

## 8. Statements at the tag that disagree

- **Code defaults are not the values in force.** The project's record set:
  - arrival 45° (default 60°);
  - flush 10 mm (default 3 mm);
  - round rule 10 mm (default 25 mm);
  - thinnest 25 mm (default 15 mm).

  (`status.md:56-63`, `:113-120`)
- **`docs/rules-by-stage.md:39-40` is partly stale.** It still lists *"cut 3 mm into the metal at
  least"* and *"1 mm of skin"*. Both went with the glue on 27 September (commit f17ef6e). Its "near
  miss ... moved inside the rule" (`:25-28`) predates *"the nudge retired"* (26 September,
  `status.md:161`).
- **`docs/data-engine-plan.md:58-60`** says the flush rule goes with touch and glue. The engineer
  kept it and raised it to 10 mm on 29 September (`status.md:113`).
- **The slot angle.** The 27 September page proposed 60° off parallel (`rib-check.html:573`). The
  record holds 30° (`rules.py:95-99`).
- **Root fillet 10 mm against 12 mm.** OPT-7's research says 12 mm; the record says 10 mm (section
  5.1).
- **`status.md:129`** says the 10 mm flush is *"not yet in a library"*. Library `9d087e38168454eb`
  and campaign RIB-16 (a campaign under the fixes) ran with it (`status.md:93`, `:152`).

---

## 9. Every rule

All values are fastcae's code defaults; values in force on the project are marked. "Where" is at
`fastcae-v1`, under `src/fastcae/` unless the path starts with `docs/`, `tools/` or `git show`.

| Rule | Value | Where | Kind | Prevents |
|---|---|---|---|---|
| Laid thickness | 25 mm | `generate/rules.py:34-37` | layer | - |
| Thickness range, cast steps | 15-25 mm in 5 mm steps; **25 mm only in force** | `generate/rules.py:38-43`; `docs/features/ribs/status.md:115` | CP-SAT, CAD check | ribs built thinner than checked (fuse drops) |
| Tallest | 5 × own thickness, and under every grip, band and kept clear | `generate/rules.py:44-47`; `rules/member.py:1234-1238` | layer, CAD check, CP-SAT | thin tall plates |
| Thinnest cast thickness for a height | max(thinnest, H/5) on a cast step | `pipeline/library.py:95-108` | CP-SAT | over-tall ribs |
| Least end height | 20 mm = 2 × root fillet | `generate/rules.py:48-53`; `rules/member.py:1239-1243` | layer, CAD check | fillets meeting over the top |
| Flush under the gripped wall's top (and over its bottom when hanging) | 3 mm; **10 mm in force** | `generate/rules.py:54-55`; `rules/member.py:538-600`; `generate/fins.py:748-776` | layer, CAD check | proud tops, flush steps, no room for the fillet |
| Wall an end grips, at least | least end + flush: 23 mm; 30 mm in force | `generate/rules.py:184-188`; `generate/screening.py:158-164` | layer | ends on walls too low to hold them |
| Top past the end stays under the grip | over 30 mm past each end | `generate/fins.py:783-804`, `:814-816` | layer | tops rising proud inside the wall |
| Top under metal overhead | 20 mm (graze); flush under the volume's top | `generate/fins.py:736-747`, `:2145-2166` | layer | thin slabs of sand over the top |
| Roof read across the whole width | 5 reads across | `generate/fins.py:1086`, `:1122-1158` | layer | tops cutting into tool spaces beside the middle |
| No sag | middle ≥ lower end | `generate/fins.py:777-782` | layer | end faces in the open |
| Base on a floor | base at the floor everywhere, + 10 mm glue, trimmed | `generate/fins.py:878-915`; `rules/attach.py:247-257`; `rules/member.py:612-642` | layer, CAD check | hovering bases, bases through floors |
| Floor rise under a floored rib | 8 mm | `rules/method.py:31-34` | CAD check | mistaking a boss for the floor |
| Core gap under a hanging base | 6 mm | `generate/rules.py:100-102`; `generate/fins.py:1074-1083` | layer | thin slots of sand |
| Ends on walls only (no rib-on-rib ends) | two ends on rails, rails ≥ 60 mm | `generate/fins.py:401-433`, `:2337-2341` | layer | floating ends |
| Arrival angle | 60°; **45° in force** | `generate/rules.py:56-63`; `part/walls.py:49-54`; `rules/member.py:430-440` | layer, CAD check | open end faces, knife-edge sand, fillets off the corner, small faces |
| Fan lean | ≤ 90° − arrival (30°; 45° in force) | `generate/rules.py:199-203` | layer | fans glancing off their boss |
| Ring chords | 4 sides (45°) | `generate/fins.py:2064-2068` | layer | chords lying along the wall |
| Aimed lines | ±25° from square, 5° steps | `generate/fins.py:2673-2676` | layer | shallow arrivals |
| A line meets a face | cosine ≥ 0.05 | `rules/method.py:35-37` | CAD check | grazing read as meeting |
| One wall across the end's face | no round, hole or edge under it | `rules/member.py:538-556`; `generate/curved.py:185-257` | layer, CAD check | ends draped over edges and rounds |
| A hollow round is a wall from | 25 mm; **10 mm in force**; never a torus or sphere | `generate/rules.py:64-67`; `part/walls.py:109-139` | layer, CAD check | ends on fillets |
| A bulging round is a wall from | 25 mm | `generate/rules.py:68-75` | layer, CAD check | ends wrapping over rounded edges |
| Whole end glued | every line over the face meets the wall before the cap | `rules/member.py:479-535` | CAD check | end faces partly in air |
| Glue drawn past the surface | 10 mm, lines cast from 20 mm back | `rules/method.py:20-30`; `rules/attach.py:65-79` | build | gaps at the joint |
| End inside its stretch of wall | half/sin(angle) − half + half a stride | `generate/fins.py:969-987` | layer | ends sliding onto corner rounds |
| Room in front of a wall | 40 mm of air | `generate/curved.py:114-117`; `generate/screening.py:88-109` | layer | ends unable to arrive square |
| Kept clear in front of an end | over its zone, full width, to least height | `generate/screening.py:170-188` | layer | ends in tool spaces |
| End zone | (T/2 + graze)/sin(arrival) = 38 mm (46 mm at 45°) | `generate/rules.py:190-197` | CAD check | false slot refusals at the joint |
| Joint's wall | host face + rounds 2 faces away + trimmed faces 3 away | `rules/member.py:172-178`, `:364-394` | CAD check | false refusals at a wall's own fillets |
| Ends apart | 45 mm centre to centre | `generate/rules.py:115-120`; `generate/choose.py:82-87` | CP-SAT | folds where ends overlap |
| Sand between ribs | 27.5 mm each side (80 mm centres at 25 mm) | `generate/rules.py:84-86`, `:210-213`; `generate/fins.py:1969-2037` | CP-SAT | thin sand between ribs |
| Sand between ribs of two volumes | 55 mm face to face, read in 3D (5 mm, then 1 mm) | `pipeline/library.py:441-505` | CP-SAT | thin sand across volumes |
| Crossing angle | ≥ 60° (junction); else conflict | `generate/rules.py:103-107`; `generate/choose.py:106-112` | CP-SAT | wedges of sand at shallow crossings |
| Crossings in the middle third | ≥ 1/3 of each run from either end | `generate/rules.py:108-114`; `generate/choose.py:113-116` | CP-SAT | folds at overlapping ends |
| Free at a shared root | first 35 % of each run | `generate/rules.py:87-89`; `generate/fins.py:1945-1966` | CP-SAT | - |
| V at a shared root | ≥ 60° within half thicknesses + 2 × root fillet | `generate/choose.py:272-302` | CP-SAT | Vs the fillets fill solid |
| Pockets (three ribs; two and a wall) | ≥ 55 mm inscribed circle | `generate/choose.py:130-261`; `pipeline/sample.py:175-176` | CP-SAT | pockets filled solid, specks |
| Plate or flange near a member | ≥ half the footprints + 55 mm in plan | `generate/choose.py:72-81` | CP-SAT | slots under plates |
| Clearance to other metal | 20 mm face to face (2 × root fillet) | `generate/rules.py:90-94`; `rules/member.py:936-1046` | layer, CAD check | thin slabs of sand, scallop faces |
| Slot | faces within 30° of parallel | `generate/rules.py:95-99` | CAD check | - |
| Middle line from metal (gate, optimisers) | T_max/2 + graze = 32.5 mm, by the millimetre | `generate/fins.py:641-692` | layer | grazing ribs |
| No run into the part between end zones; not cut in two | - | `rules/member.py:215-232`, `:973-986` | CAD check | ribs through walls |
| Hole's tool kept clear | 1.8 × radius, 3 diameters past each end | `generate/rules.py:127-130` | layer, CAD check | ribs in tool spaces |
| Past a bore, along a bearing's line | bore + 5 mm | `generate/rules.py:131-133` | layer, CAD check | ribs in shaft paths |
| Register | under 0.1 × diameter deep | `generate/rules.py:134-136` | layer | - |
| Lid in front of a held face | 8 mm | `generate/rules.py:142-144` | layer, CAD check | ribs on mating faces |
| A bore or boss | faces wrapping ≥ 100° | `input/features.py:42-48` | layer | slivers of curves read as bores |
| Length | 75 mm (3 × laid) to 500 mm | `generate/rules.py:79-83` | layer, CAD check | stubs, overlong ribs |
| Bend | radius ≥ 200 mm, exact tightest station | `generate/rules.py:76-78`; `generate/fins.py:1892-1936` | layer, CAD check | folds, hairpins |
| Control points | first 0.15-0.5, second 0.5-0.85 of the chord; ≤ 40 mm across | `generate/fins.py:1161-1165`, `:2073` | layer | self-looping curves |
| Members a design | ≤ 24 | `pipeline/sample.py:177` | CP-SAT | - |
| Draft | 1° each face | `generate/rules.py:145-147`; `member/spec.py:327-334` | layer, CAD check | ribs that will not leave the mould |
| Tip | ≥ 10 mm after draft | `generate/rules.py:148-150`; `rules/member.py:1254` | CAD check | tops too thin |
| Tip guard | ≥ 2r + 2 = 12 mm | `docs/archive/pages/2026-09-26-glue-rulebook.html:301` | proposed | edge rounds meeting |
| Rib against wall | 0.8 × wall (field era, assumed); none at the tag | `docs/archive/generate.md:219-225`; `docs/code-map.md:174` | dropped / proposed | hot spots at thin walls |
| Undercut | none, by construction (along the draw) | `docs/archive/rib-optimisation-plan.md:85-89` | layer | undercuts |
| Metal along the pull from a tip | rejected every design | `docs/archive/generate.md:434-437` | dropped | - |
| Plates across the pull | only where open; underside by a core | `docs/features/ribs/families-plan.md:56-58` | layer | undercuts |
| Boss cover | 80 % of the boss's height | `docs/archive/rib-optimisation-plan.md:375-377` | dropped (24-26 Sept) | ribs over a boss sliver |
| End cut and skin | 3 mm in, 1 mm skin | `git show 4a5130e:src/fastcae/generate/rules.py` | dropped (27 Sept) | ends short of metal |
| T-section web into flange; flange past the web | 0.5 × flange thickness; 1 mm | `member/solid.py:49-54` | build | coincident faces |
| Flange taper | over 1 × flange width to the web | `pipeline/library.py:179-191` | layer | flange ends overhanging walls |
| Inverted T: web over flange at each end | ≥ 5 mm | `pipeline/library.py:225-251` | layer | - |
| Root fillet | 10 mm | `generate/rules.py:123-124` | mesher | sharp roots |
| Edge round, top included | 5 mm | `generate/rules.py:125-126`; `shape/band.py:452-457` | mesher | sharp free edges |
| Rib-rib junction fillet | root fillet, pair by pair; pockets filleted at corners | `shape/band.py:484-499` | mesher | sharp junctions |
| Fillet fallback | 5, then 2.5 mm, then sharp (3 tries, 10 mm wider each) | `shape/band.py:66-79` | mesher | lost designs at tight corners |
| Fillets in the CAD | 0 of 42 on fused seams | `docs/research/2026-09-26-issue-catalogue.md:175` | dropped | - |
| Root fillet mesh density | 12 elements a turn | `shape/band.py:898-903`; `simulate/face_mesh.py:272-282` | mesher | misread stress at roots |
| Curved edges | 8 a turn, ≥ 1 mm | `simulate/face_mesh.py:106-111` | mesher | polygonal holes |
| Narrow face rim | 3 × width, ≥ 8 mm | `simulate/face_mesh.py:387-408` | mesher | needles on strips |
| Edge collapse | < 3 mm, ≤ 4 nodes, never by deck faces | `simulate/face_mesh.py:116-123` | mesher | too many unknowns |
| Weld | 0.1 mm | `simulate/face_mesh.py:113-115` | mesher | cracks between faces |
| Least element | 4 mm | `simulate/face_mesh.py:53` | mesher | - |
| Draw an end past its cut | 10 mm, cut by a half-space | `member/solid.py:28-32`, `:132-161` | build | films, second solids |
| End cuts | planes only, never coaxial cylinders | `part/walls.py:164-170` | build | fuses to nothing |
| Trim before fuse | keep the piece holding the middle | `member/solid.py:164-215` | build | stray slivers breaking fuses |
| Sections near the ends | every 0.5 mm within 40 mm | `generate/curved.py:29-35` | build | edges flush with walls |
| Fuse | one non-destructive boolean, then one at a time; 1 µm fuzzy retry | `generate/cad.py:124-310` | build | stacked tolerances, dropped ribs |
| Each candidate fused alone at placement | one valid solid | `pipeline/library.py:389-408` | CAD check | designs losing ribs |
| One solid; part kept; tools held | ≥ 99 % of the part; 6 points a tool | `generate/cad.py:61-66`, `:300-310` | build | silent drops |
| Metal added against planned | 0.8-1.2 | `generate/build.py:249` | build | lost metal |
| Smallest new face | 5 mm² (reported in campaigns) | `generate/rules.py:121-122`; `generate/build.py:93-98`; `generate/workflow.py:535` | build | slivers |
| Built against drawn | 1.0 / 1.0 / 0.5 mm | `docs/features/ribs/next-plan.md:202-203` | proposed | silent reshaping |
| Narrow face width | 2·area/perimeter < 8 mm | `tools/analysis/cad_new_narrow_faces.py:19` | proposed (never run) | strips the area judge misses |
| Knife edges | normals within 8° of opposite | `tools/analysis/cad_knife_edges.py:24` | proposed (never run) | unmeshable wedges |
| Mesh gate | ≤ 0.08 % tets under q 0.1; none inverted; ≤ 415,000 TET10 | `generate/build.py:33-34`; `generate/records.py:20` | build (mesh check) | unusable meshes |
