# Example contracts

The checks of CON-1 (contract schema v0) load these contracts as an outside user would.
- Each file is written by `make_examples.py`.
- Each value carries its source: a paper's table, a standard's clause, the engineer's decision, or an assumption listed in the file.
- Nothing comes from GRC.

Regenerate after any change:

    uv run python checks/data/contracts/make_examples.py

The checks fail if a file is stale.

| File | Stage | Style | Sources |
|---|---|---|---|
| `hofstetter2018_posed.json` | posed | package | Hofstetter et al. 2018, Forsch Ingenieurwes 82:361-370. Table 2: 165 mm, 9.32 ± 1 %, 366 N·m nominal input, 15,000 rpm, 944 h, 20MnCr5. Table 3 (benchmark): bearings 6206, NU205-E, 32010, 32010, 6012, 6011. Assumptions A1-A8 |
| `agri_ev_gearbox_posed.json` | posed | gear_train | Kim et al. 2024, Sci Rep 14:4145. Table 1: the full gear train. Table 3: the aluminium card (E 70.93 GPa, ν 0.3135, ρ 2,660 kg/m³, 23.1 µm/(m·K)). p. 2: 7 kW at 2,650 rpm. Son et al. 2020 p. 3: total ratio 12.37. The torque is taken from the power (A1), because the paper's "22 Nm" conflicts with its 7 kW |
| `textbook_two_bearing_derived.json` | derived | gear_train | One helical gear between two bearings: fastcae's gearbox-engineering report §6.2, a worked example on JTEKT eq. 5-29 (T 300 N·m, d 60 mm, αn 20°, β 25°, 120 mm span). Its seat loads are stamped `manual-1` |

**Re-read from the PDFs on 8 October 2026** with pypdf: Kim et al. 2024 Tables 1 and 3, and Hofstetter et al. 2018 Tables 2 and 3.

**Still to check:**
- Each bearing's outside diameter and width: ISO 15 values as maker catalogues list them, not yet compared with a catalogue.
- The reading of Hofstetter's "Total center distance" as the input-to-output offset, against the paper's Fig. 4.
- Which bearing of each shaft sits in the main housing (A8).

**Shared defaults** (spec §4.5-4.6):
- **Standards and guidelines:**
  - NADCA 2015 draft (2° inside, 1° outside), with 0.25 mm machining stock;
  - Shigley's tilt limits at the lower end;
  - Marano et al.'s 3 % order separation;
  - a 25 % model margin.
- **The engineer's:** the 4 mm minimum wall (D7).
- **An assumption:** the housing's share of each tolerance, half (A6).
