# zenryx (repository: fastcae-sim)

A platform that designs housings from requirements. An engineer gives a gearbox's functional interfaces, loads, package, targets and one manufacturing process. Agents run design campaigns over deterministic tools, and every design comes back FE-proven, with the whole trajectory of decisions and consequences kept as data. The first family is an EV single-speed two-stage reducer housing, printed by LPBF with machined interfaces (decisions pending).

**Status:** set up on 7 October 2026. The plan is for the engineer's review, and no code is written yet.

**Start here:**
- [CLAUDE.md](CLAUDE.md): how the work is organised.
- [docs/status.md](docs/status.md): the board.
- [docs/features/product/plan.md](docs/features/product/plan.md): the plan.
- [docs/features/product/decisions.md](docs/features/product/decisions.md): the decisions, with their evidence.

The plans of 4-5 October (cast housings in FreeCAD benchmarked on GRC; sheet-metal brackets) are in [docs/archive/](docs/archive/), superseded.

**Relation to fastcae.** fastcae (`C:\Work\fastcae`) is the earlier rib application, frozen at its tag `fastcae-v1`. zenryx imports nothing from it. Code it has proven is copied in when needed, each copy with a parity test. fastcae's research library and inputs are read in place.

**Data policy:** third-party part inputs (CAD, drawings, decks) and run outputs never enter git; see `.gitignore`.
