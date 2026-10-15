#!/usr/bin/env bash
# PROTOTYPE (LOP-30, 15 October).
# Judge an already drawn design: FE under the memory guard, then oil-tight, castability and the grade (as campaign_run.sh
# does after its drawing). Run: bash judge_drawn.sh <design>
set -u
cd "$(dirname "$0")/../.." || exit 1
PY=.venv/Scripts/python.exe
D="$1"
OUTD=data/first_loop
rm -f "$OUTD/memory_guard_$D.stopped"
"$PY" prototypes/first_loop/memory_guard.py "$D" --floor-mb "${GUARD_FLOOR:-600}" --strikes "${GUARD_STRIKES:-4}" --most 1.5 > /dev/null 2>&1 &
G=$!
echo "[$(date +%H:%M:%S)] FE $D"
"$PY" prototypes/first_loop/fe.py "$D" 8.0 > "$OUTD/fe_$D.log" 2>&1
echo "[$(date +%H:%M:%S)] FE exit $?: $(grep -E 'peak drive:|clashes' "$OUTD/fe_$D.log" | cut -c1-200 | tr '\n' ' ')"
kill "$G" 2>/dev/null
if [ -f "$OUTD/memory_guard_$D.stopped" ]; then echo "STOPPED by the memory guard"; exit 1; fi
echo "[$(date +%H:%M:%S)] oil-tight"
"$PY" prototypes/first_loop/oiltight.py "$D" > "$OUTD/oiltight_$D.log" 2>&1; tail -n 2 "$OUTD/oiltight_$D.log"
echo "[$(date +%H:%M:%S)] castability"
"$PY" prototypes/first_loop/castable.py "$D" > "$OUTD/castable_$D.log" 2>&1; tail -n 3 "$OUTD/castable_$D.log"
"$PY" prototypes/first_loop/grade.py > "$OUTD/grade_$D.log" 2>&1; grep -E "^$D " "$OUTD/grade_$D.log"
echo "[$(date +%H:%M:%S)] done $D"
