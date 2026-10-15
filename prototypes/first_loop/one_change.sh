#!/usr/bin/env bash
# PROTOTYPE (LOP-25; the engineer, 12 October 13:33: "why not perform those operations on the same housing", one change at
# a time): the step loop's runs. Each line of changes is one run on the base set-up (`mm12`: 5.5 kg, peak drive, 4 mm, the
# band 24, the least member 8, the greatest member 12, every tilt and bed held with the factor 1.15), drawn smooth
# (LOOP_SDF=3), judged by FE, castability (the lump gate) and the grade, pictured face-on. One job at a time.
#
#   one_change.sh <tag>:"<extra topo_free arguments>":"<extra environment>" ...
#   e.g. one_change.sh p40::LOOP_MEMBER_P=40 webcap:"--space web12.npz":
#
# Results: data/first_loop/one_change.log (a line a run); the designs <tag>_free.
cd "$(dirname "$0")/../.."
PY=.venv/Scripts/python.exe
LOG=data/first_loop/one_change.log
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
run_of() { grep -o "done in [0-9]* s; .*" "$1" | tail -1 | sed 's/.*; //'; }
for spec in "$@"; do
  T="${spec%%:*}"
  rest="${spec#*:}"
  EXTRA="${rest%%:*}"
  ENVS="${rest#*:}"
  say "$T: topo_free $EXTRA ($ENVS)"
  env PYTHONIOENCODING=utf-8 LOOP_LEAST_MEMBER=8 $ENVS $PY prototypes/first_loop/topo_free.py 5.5 4 200 --objective compliance_tilt --beds \
    --cases "peak drive" --route split --settle 0.02 --every 25 --beta-most 32 --fast --max-member 12 --band 24 --height-field 6 \
    --safety 1.15 $EXTRA --tag "$T" > "data/first_loop/topo_$T.log" 2>&1
  RUN=$(run_of "data/first_loop/topo_$T.log")
  [ -n "$RUN" ] || { say "$T: the run failed: $(tail -2 data/first_loop/topo_$T.log)"; continue; }
  say "$T: $(grep -o 'the binary check: .*' data/first_loop/topo_$T.log | tail -1)"
  env PYTHONIOENCODING=utf-8 LOOP_SDF=3 $PY prototypes/first_loop/propose.py "${T}_free" --run "$RUN" > "data/first_loop/propose_$T.out" 2>&1
  say "$T: $(tail -1 data/first_loop/propose_$T.out)"
  env PYTHONIOENCODING=utf-8 $PY prototypes/first_loop/look.py "${T}_free" face > "data/first_loop/look_face_$T.log" 2>&1
done
say "done"
