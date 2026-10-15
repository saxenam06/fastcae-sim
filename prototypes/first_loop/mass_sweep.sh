#!/usr/bin/env bash
# The free run's mass sweep (LOP-24; the engineer, 11 October 20:04: "a good strategy which can be later
# given to the agent to start from"): the height field's free run (outcome_hf6_4mm_7.0kg's settings)
# with the optimiser's factor of safety, at each budget, one run at a time; then the same at one
# budget with a smaller plan smoothing. Only the optimisations: each field is read (which members
# appear at the least mass, which recur) before any is drawn and judged.
#   mass_sweep.sh "<budget> <budget> ..." [safety] [smoothing mm] [extra budget:smoothing ...]
# Each run's log: data/first_loop/optimise_sweep_<tag>.log; a summary line per run in
# data/first_loop/mass_sweep.log. Calls the venv's python directly (concurrent `uv run` exits 127),
# retrying a start that failed within seconds only.
set -u
cd "$(dirname "$0")/../.."
PY=.venv/Scripts/python.exe
BUDGETS=${1:-"5.5 6.0 6.5 7.0 7.5"}
SAFETY=${2:-1.15}
SMOOTH=${3:-6}
EXTRA=${4:-"6.5:5"}
SUMMARY=data/first_loop/mass_sweep.log

run_one() {
  local budget=$1 smooth=$2
  local tag="hfsf_4mm_${budget}kg_r${smooth}"
  local log="data/first_loop/optimise_sweep_${tag}.log"
  local tries=0 code=0 started
  while :; do
    started=$(date +%s)
    "$PY" prototypes/first_loop/topo_free.py "$budget" 4 200 --objective compliance_tilt --beds --cases "peak drive" --route split \
      --settle 0.02 --every 25 --beta-most 32 --fast --max-member 0 --band 24 --height-field "$smooth" --safety "$SAFETY" \
      --tag "$tag" > "$log" 2>&1
    code=$?
    if [ "$code" = "127" ] && [ $(( $(date +%s) - started )) -lt 20 ] && [ "$tries" -lt 3 ]; then
      tries=$((tries + 1)); sleep 5; continue
    fi
    break
  done
  local done_line
  done_line=$(grep -a "done in" "$log" | tail -1)
  echo "$(date '+%H:%M') budget ${budget} kg, smoothing ${smooth} mm, safety ${SAFETY}: exit ${code}; ${done_line}" >> "$SUMMARY"
}

echo "$(date '+%H:%M') sweep: budgets ${BUDGETS}, safety ${SAFETY}, smoothing ${SMOOTH} mm; then ${EXTRA}" >> "$SUMMARY"
for b in $BUDGETS; do run_one "$b" "$SMOOTH"; done
for pair in $EXTRA; do run_one "${pair%%:*}" "${pair##*:}"; done
echo "$(date '+%H:%M') sweep done" >> "$SUMMARY"
