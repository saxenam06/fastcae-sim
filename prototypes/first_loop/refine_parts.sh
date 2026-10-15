#!/usr/bin/env bash
# PROTOTYPE (LOP-26, Refine's last half): a reading's parts moved and sized (`topo_free.py --parts`), what moved pictured
# (`parts_compare.py`), then drawn and judged (`LOOP_PARTS` with `propose.py`) and pictured face-on. One job at a time.
#
#   refine_parts.sh <reading label> <tag> <the parts' budget kg>
#
# Results: data/first_loop/refine_parts_<tag>.log; the comparison <tag>_compare.png; the design <tag>_parts.
cd "$(dirname "$0")/../.."
PY=.venv/Scripts/python.exe
R=$1
T=$2
B=$3
LOG=data/first_loop/refine_parts_$T.log
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
run_of() { grep -o "done in [0-9]* s; .*" "$1" | tail -1 | sed 's/.*; //'; }
export PYTHONIOENCODING=utf-8 LOOP_LEAST_MEMBER=8

$PY prototypes/first_loop/topo_free.py "$B" 4 200 --objective compliance_tilt --beds --cases "peak drive" --route split \
  --settle 0.02 --every 25 --beta-most 32 --fast --max-member 0 --band 24 --height-field 6 --safety 1.15 \
  --parts "${R}.json" --beta0 4 --tag "$T" > "data/first_loop/topo_${T}parts.log" 2>&1
PARTS=$(run_of "data/first_loop/topo_${T}parts.log")
[ -n "$PARTS" ] || { say "the parts' run failed: $(tail -2 data/first_loop/topo_${T}parts.log)"; exit 1; }
say "parts: $PARTS; $(grep -o 'the binary check: .*' data/first_loop/topo_${T}parts.log | tail -1)"
$PY prototypes/first_loop/parts_compare.py "$R" "$PARTS" --label "${T}_compare" > "data/first_loop/compare_${T}.log" 2>&1
LOOP_PARTS="${PARTS}_parts.json" $PY prototypes/first_loop/propose.py "${T}_parts" --run "$PARTS" > "data/first_loop/propose_${T}.out" 2>&1
say "judged: $(tail -1 data/first_loop/propose_${T}.out)"
$PY prototypes/first_loop/look.py "${T}_parts" face > "data/first_loop/look_face_${T}.log" 2>&1
say "done"
