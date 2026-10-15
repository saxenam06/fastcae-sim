#!/usr/bin/env bash
# PROTOTYPE (LOP-28) - one design of the overnight campaign (the engineer, 13 October 00:16: "go step by step"): its
# proposal (`propose.py`: the optimisation, the drawing, FE beside castability, the grade, the pictures) under the memory
# guard (`memory_guard.py`: the run ended if the available memory stays under 900 MB), then each half's face along the pull
# (`look.py <design> face`). Environment variables (LOOP_MEMBER_LEVEL, LOOP_EXACT_WALLS, ...) pass through.
# Run: bash prototypes/first_loop/campaign_run.sh <design> <propose.py's arguments after the design...>
set -u
cd "$(dirname "$0")/../.."
PY=.venv/Scripts/python.exe
OUTD=data/first_loop
D="$1"
shift
"$PY" prototypes/first_loop/memory_guard.py "$D" --floor-mb "${GUARD_FLOOR:-900}" --strikes "${GUARD_STRIKES:-3}" --most 1.5 > /dev/null 2>&1 &
guard=$!
"$PY" prototypes/first_loop/propose.py "$D" "$@" > "$OUTD/propose_$D.out" 2>&1
code=$?
tail -1 "$OUTD/propose_$D.out"
if [ $code -eq 0 ] && [ -f "$OUTD/${D}_cover.ply" ]; then
  "$PY" prototypes/first_loop/look.py "$D" face > "$OUTD/look_face_$D.log" 2>&1
fi
wait $guard 2> /dev/null
if [ -f "$OUTD/memory_guard_$D.stopped" ]; then
  echo "STOPPED by the memory guard: $(cat "$OUTD/memory_guard_$D.stopped")"
fi
echo "done $D (exit $code)"
