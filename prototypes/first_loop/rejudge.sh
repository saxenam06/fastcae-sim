#!/usr/bin/env bash
# PROTOTYPE (LOP-23) - judge designs again by FE, one at a time, then grade them all: after a change
# to the judge (11 October 08:45: FE's surface 9 mm -> 7 mm, `fe.SURFACE_EDGE`).
#
# Run: bash prototypes/first_loop/rejudge.sh <design> ...
set -u
cd "$(dirname "$0")/../.."
PY=.venv/Scripts/python.exe
for d in "$@"; do
    while [ -e data/first_loop/gpu_hold ]; do sleep 20; done
    "$PY" prototypes/first_loop/fe.py "$d" 8.0 > "data/first_loop/fe_$d.log" 2>&1
    echo "$(date +%H:%M:%S) $d exit $?: $(grep -E 'peak drive:' "data/first_loop/fe_$d.log" | cut -c12-90)"
done
"$PY" prototypes/first_loop/grade.py > data/first_loop/grade_rejudge.log 2>&1
"$PY" prototypes/first_loop/names.py > /dev/null 2>&1
echo "$(date +%H:%M:%S) graded"
