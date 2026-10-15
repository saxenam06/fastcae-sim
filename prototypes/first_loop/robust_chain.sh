#!/usr/bin/env bash
# PROTOTYPE (LOP-18) - the loop's best topology optimisation so far, as one chain on the GPU, one
# stage at a time (the engineer, 10 October 14:50: "choose your best method of topology
# optimisation so far, robust, efficient and fast"), on the contract's layout:
#   1. the split route, plain, from nothing: where the material wants to go;
#   2. robust from it (an eroded, a nominal and a dilated design all held: the shape holds at
#      ±1 voxel), from sharpness 8;
#   3. sharpened to 32 from it, which ends with the binary check (the field at 0.5, metal or air).
# The same settings as the night's chain that gave outcome_robust_b32, with fewer iterations.
# Each stage's field goes to the Designs page's Optimisation tab as it ends (topo_export.py).
#
# Usage: [OBJECTIVE=misalignment_pnorm] [FAST=1] robust_chain.sh [budget kg] [cases] [stage-1 its] [stage-2 its] [stage-3 its]
#   e.g. OBJECTIVE=misalignment_pnorm FAST=1 robust_chain.sh 7.73 "peak drive" 120 60 50
#   OBJECTIVE: misalignment_bound (every seat bounded, the default) or misalignment_pnorm (one
#   p-norm of them: one adjoint a case, LOP-19); FAST=1: the GPU's assembly, kept factor and MMA
#   subproblem (topo_free.py --fast). Logs: data/first_loop/chain_contract_<objective>_<cases>_s<n>.log
set -u
cd "$(dirname "$0")/../.." || exit 1
B="${1:-7.73}"
CASES="${2:-}"
N1="${3:-80}"
N2="${4:-50}"
N3="${5:-50}"
OBJECTIVE="${OBJECTIVE:-misalignment_bound}"
FAST="${FAST:-0}"
PY=.venv/Scripts/python.exe
OUT=data/first_loop
ONLY=""
if [ -n "$CASES" ] && [ "$CASES" != "peak drive,peak reverse" ]; then
  ONLY="$(echo "$CASES" | sed 's/peak //g; s/,/_/g')_"
fi
# The stems topo_free.py gives these runs (its run_stem: objective, route, contract, cases, tag, robust).
BASE="topofree_${OBJECTIVE}_${B}kg_6mm_projected_cup_bolts_skin4_split_contract_${ONLY}"
S1="${BASE%_}"
S2="${BASE}robust0.15"
S3="${BASE}b32_robust0.15"
LOG="$OUT/chain_contract_${OBJECTIVE#misalignment_}_${ONLY}"
CASE_ARGS=(--objective "$OBJECTIVE")
[ -n "$CASES" ] && CASE_ARGS+=(--cases "$CASES")
[ "$FAST" = "1" ] && CASE_ARGS+=(--fast)

run() {  # a concurrent python start can exit 127 at random: retry on 127 only, and only a start that
  # failed within seconds. A stage killed after it began exits 127 too, and must stay dead: a retry
  # restarted one five seconds after it was ended (10 October 15:21), and it ran beside the next.
  local code=0 began
  for attempt in 1 2 3; do
    began=$SECONDS
    "$PY" "$@"
    code=$?
    if [ "$code" -ne 127 ] || [ $((SECONDS - began)) -gt 10 ]; then
      return "$code"
    fi
    sleep 5
  done
  return "$code"
}

stage() {  # <log> <script> <args...>: one stage, its start and exit in its log
  local log="$1"
  shift
  echo "[$(date '+%H:%M:%S')] start: $*" >> "$log"
  run "$@" >> "$log" 2>&1
  local code=$?
  echo "[$(date '+%H:%M:%S')] exit $code" >> "$log"
  return "$code"
}

stage "${LOG}s1.log" prototypes/first_loop/topo_free.py "$B" 6 "$N1" --route split ${CASE_ARGS[@]+"${CASE_ARGS[@]}"} || exit 1
run prototypes/first_loop/topo_export.py "$S1" >> "${LOG}s1.log" 2>&1
stage "${LOG}s2.log" prototypes/first_loop/topo_free.py "$B" 6 "$N2" --route split --robust 0.15 --robust-p 16 \
  --start "$S1" --beta0 8 --ramp 0 ${CASE_ARGS[@]+"${CASE_ARGS[@]}"} || exit 2
run prototypes/first_loop/topo_export.py "$S2" >> "${LOG}s2.log" 2>&1
stage "${LOG}s3.log" prototypes/first_loop/topo_free.py "$B" 6 "$N3" --route split --robust 0.15 --robust-p 16 \
  --start "$S2" --beta0 32 --ramp 0 --tag b32 ${CASE_ARGS[@]+"${CASE_ARGS[@]}"} || exit 3
run prototypes/first_loop/topo_export.py "$S3" >> "${LOG}s3.log" 2>&1
echo "[$(date '+%H:%M:%S')] chain done: $S3" >> "${LOG}s3.log"
