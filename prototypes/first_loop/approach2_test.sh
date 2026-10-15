#!/usr/bin/env bash
# PROTOTYPE (LOP-25, approach 2's first test; the engineer, 12 October 09:54: "try"): three designs, one job at a time.
#   a2_c1  generator C alone: the free run optimised again with the least member (8 mm: no paint), drawn smooth
#   a2_b1  generator B alone: the benchmark's members along their skeleton
#   a2_bc  B then C: B's members as the design space (`b_space.py`), optimised with the least member, drawn smooth
# Each is judged by propose.py (FE beside castability, the grade, the pictures, the Designs page). Waits for the
# C1 optimisation started before it. Results: data/first_loop/approach2_test.log
cd "$(dirname "$0")/../.."
PY=.venv/Scripts/python.exe
LOG=data/first_loop/approach2_test.log
BENCH=topofree_compliance_tilt_5.5kg_4mm_projected_band24_cup_bolts_split_contract_drive_hfsf_4mm_5.5kg_r6_hf6_single_flange_beds_sf1.15
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
run_of() { grep -o "done in [0-9]* s; .*" "$1" | tail -1 | sed 's/.*; //'; }

say "waiting for c1's optimisation"
until grep -q "done in" data/first_loop/topo_c1.log 2>/dev/null; do sleep 5; done
C1=$(run_of data/first_loop/topo_c1.log)
say "c1: $C1"
LOOP_SDF=3 PYTHONIOENCODING=utf-8 $PY prototypes/first_loop/propose.py a2_c1 --run "$C1" > data/first_loop/propose_a2_c1.out 2>&1
say "a2_c1: $(tail -1 data/first_loop/propose_a2_c1.out)"

LOOP_SKELETON=1.0:20:16 PYTHONIOENCODING=utf-8 $PY prototypes/first_loop/propose.py a2_b1 --run "$BENCH" > data/first_loop/propose_a2_b1.out 2>&1
say "a2_b1: $(tail -1 data/first_loop/propose_a2_b1.out)"

PYTHONIOENCODING=utf-8 $PY prototypes/first_loop/b_space.py "$BENCH" a2_b1 --label a2_bspace --grow 1 > data/first_loop/b_space_a2.log 2>&1
say "b_space: $(tail -2 data/first_loop/b_space_a2.log | head -1)"
LOOP_LEAST_MEMBER=8 PYTHONIOENCODING=utf-8 $PY prototypes/first_loop/topo_free.py 5.5 4 200 --objective compliance_tilt --beds --cases "peak drive" \
  --route split --settle 0.02 --every 25 --beta-most 32 --fast --max-member 0 --band 24 --height-field 6 --safety 1.15 \
  --space data/first_loop/a2_bspace.npz --tag bc > data/first_loop/topo_bc.log 2>&1
BC=$(run_of data/first_loop/topo_bc.log)
say "bc: $BC"
LOOP_SDF=3 PYTHONIOENCODING=utf-8 $PY prototypes/first_loop/propose.py a2_bc --run "$BC" > data/first_loop/propose_a2_bc.out 2>&1
say "a2_bc: $(tail -1 data/first_loop/propose_a2_bc.out)"
say "done"
