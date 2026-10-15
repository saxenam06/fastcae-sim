#!/usr/bin/env bash
# PROTOTYPE (LOP-26, Refine end to end; the engineer, 12 October 12:05-12:43: the gap between members in the optimisation
# itself, 20 mm): a free run with the least member and the members' plan rule (members at most a width wide and a gap
# apart), read as production's parts (`refine_read.py`), the parts moved and sized (`topo_free.py --parts`), what moved
# pictured (`parts_compare.py`), then drawn and judged (`LOOP_PARTS` with `propose.py`). One job at a time.
#
#   refine_chain.sh <label> <free run's budget kg> <the parts' budget kg> <plan gap mm> <plan width mm>
#
# Results: data/first_loop/refine_chain_<label>.log (a line a stage); the reading <label>.json/.png, the comparison
# <label>_compare.png, the design <label>_parts (its flow, FE, grade, pictures).
cd "$(dirname "$0")/../.."
PY=.venv/Scripts/python.exe
L=$1
B_FREE=$2
B_PARTS=$3
GAP=$4
WIDTH=$5
LOG=data/first_loop/refine_chain_$L.log
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
run_of() { grep -o "done in [0-9]* s; .*" "$1" | tail -1 | sed 's/.*; //'; }
export PYTHONIOENCODING=utf-8 LOOP_LEAST_MEMBER=8

say "the free run: $B_FREE kg, members at most $WIDTH mm wide and $GAP mm apart, at least 8 mm tall"
$PY prototypes/first_loop/topo_free.py "$B_FREE" 4 200 --objective compliance_tilt --beds --cases "peak drive" --route split \
  --settle 0.02 --every 25 --beta-most 32 --fast --max-member 0 --band 24 --height-field 6 --safety 1.15 \
  --plan-gap "$GAP" --plan-width "$WIDTH" --tag "${L}free" > "data/first_loop/topo_${L}free.log" 2>&1
FREE=$(run_of "data/first_loop/topo_${L}free.log")
[ -n "$FREE" ] || { say "the free run failed: $(tail -2 data/first_loop/topo_${L}free.log)"; exit 1; }
say "free: $FREE; $(grep -o 'the binary check: .*' data/first_loop/topo_${L}free.log | tail -1)"

$PY prototypes/first_loop/refine_read.py "$FREE" --label "$L" --prune 12 --tol 6 > "data/first_loop/read_${L}.log" 2>&1 || { say "the reading failed: $(tail -3 data/first_loop/read_${L}.log)"; exit 1; }
say "read: $(grep -o '"families": {[^}]*}' data/first_loop/${L}.json | head -1)"

$PY prototypes/first_loop/topo_free.py "$B_PARTS" 4 200 --objective compliance_tilt --beds --cases "peak drive" --route split \
  --settle 0.02 --every 25 --beta-most 32 --fast --max-member 0 --band 24 --height-field 6 --safety 1.15 \
  --parts "${L}.json" --beta0 4 --tag "$L" > "data/first_loop/topo_${L}parts.log" 2>&1
PARTS=$(run_of "data/first_loop/topo_${L}parts.log")
[ -n "$PARTS" ] || { say "the parts' run failed: $(tail -2 data/first_loop/topo_${L}parts.log)"; exit 1; }
say "parts: $PARTS; $(grep -o 'the binary check: .*' data/first_loop/topo_${L}parts.log | tail -1)"
$PY prototypes/first_loop/parts_compare.py "$L" "$PARTS" --label "${L}_compare" > "data/first_loop/compare_${L}.log" 2>&1

LOOP_PARTS="${PARTS}_parts.json" $PY prototypes/first_loop/propose.py "${L}_parts" --run "$PARTS" > "data/first_loop/propose_${L}.out" 2>&1
say "judged: $(tail -1 data/first_loop/propose_${L}.out)"
$PY prototypes/first_loop/look.py "${L}_parts" face > "data/first_loop/look_face_${L}.log" 2>&1
say "done"
