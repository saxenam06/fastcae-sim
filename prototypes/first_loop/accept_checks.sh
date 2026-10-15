#!/usr/bin/env bash
# PROTOTYPE (LOP-30, 15 October).
# The night's acceptance gates on a finished design (after its flow: FE, castability and the pictures are the flow's own):
# the lumps (no section over 16 mm outside the bosses and eyes), the free ends' steps, close-ups, and a sheet beside spl3
# and lw8. Run: bash accept_checks.sh <design>
set -u
cd "$(dirname "$0")/../.." || exit 1
PY=.venv/Scripts/python.exe
D="$1"
echo "[$(date +%H:%M:%S)] lumps"
"$PY" prototypes/first_loop/lump_where.py "$D" > "data/first_loop/accept_lumps_$D.log" 2>&1; grep -E "largest section" "data/first_loop/accept_lumps_$D.log"
echo "[$(date +%H:%M:%S)] steps"
"$PY" prototypes/first_loop/free_end_steps.py "$D" > "data/first_loop/accept_steps_$D.log" 2>&1; grep -E "rises over" "data/first_loop/accept_steps_$D.log"
echo "[$(date +%H:%M:%S)] close-ups"
"$PY" prototypes/first_loop/closeups.py "$D" > "data/first_loop/accept_closeups_$D.log" 2>&1; tail -n 1 "data/first_loop/accept_closeups_$D.log"
echo "[$(date +%H:%M:%S)] sheet"
"$PY" prototypes/first_loop/compare_sheet.py "compare_$D.png" "$D:$D (smooth top, window for ribs, width and gap held, from spl3)" \
  "baseline2_spl3:baseline2_spl3 (the free spline run)" "baseline2_lw8:baseline2_lw8 (cubes, passes)" > "data/first_loop/accept_sheet_$D.log" 2>&1
tail -n 1 "data/first_loop/accept_sheet_$D.log"
echo "[$(date +%H:%M:%S)] done"
