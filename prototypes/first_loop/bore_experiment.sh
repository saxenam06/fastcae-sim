#!/usr/bin/env bash
# The bore experiment (LOP-24; the plan's §9 step 2, the engineer, 11 October 23:20): each branch's
# least-metal run (`topo_free.py --objective mass_tilt`, the margins 1.25 on the tilt and 1.5 on the
# beds, the height field smoothed 6 mm), its region round one bore given to the features of
# data/first_loop/bore_<family>.json (`bore_branches.py`; the family "free" has none: the reference),
# then its FE judgement drawn plainly (`propose.py --run`), the design named bore_<family>_<kg>kg by its
# model mass. One job at a time; the symmetric factorisation (the SPD one hung on restricted spaces).
#   bore_experiment.sh ["<family> ..."]   (default: spokes web ties free)
# Each run's log: data/first_loop/optimise_bore_<family>.log; a line a step in data/first_loop/bore_experiment.log.
# Calls the venv's python directly (concurrent `uv run` exits 127), retrying a start that failed within seconds only.
set -u
cd "$(dirname "$0")/../.."
PY=.venv/Scripts/python.exe
FAMILIES=${1:-"spokes web ties free"}
SUMMARY=data/first_loop/bore_experiment.log
export LOOP_FACTOR_KIND=SYMMETRIC

echo "$(date '+%H:%M') the bore experiment: ${FAMILIES}" >> "$SUMMARY"
for fam in $FAMILIES; do
  tag="bore_${fam}"
  feat=()
  [ "$fam" != "free" ] && feat=(--height-features "bore_${fam}.json")
  log="data/first_loop/optimise_${tag}.log"
  tries=0
  while :; do
    started=$(date +%s)
    "$PY" prototypes/first_loop/topo_free.py 7.73 4 200 --objective mass_tilt --beds --cases "peak drive" --route split \
      --settle 0.02 --every 25 --beta-most 32 --fast --max-member 0 --band 24 --height-field 6 --safety 1.25 --safety-beds 1.5 \
      --tag "$tag" "${feat[@]}" > "$log" 2>&1
    code=$?
    if [ "$code" = "127" ] && [ $(( $(date +%s) - started )) -lt 20 ] && [ "$tries" -lt 3 ]; then
      tries=$((tries + 1)); sleep 5; continue
    fi
    break
  done
  stem=$(grep -a "done in" "$log" | tail -1 | sed 's/.*; //')
  echo "$(date '+%H:%M') ${tag}: optimised, exit ${code}; ${stem}" >> "$SUMMARY"
  [ -z "$stem" ] && continue
  kg=$("$PY" -c "import json,sys; r=json.load(open('data/first_loop/'+sys.argv[1]+'.json')); print(f\"{r['frozen_kg']+r['binary']['mass_kg']:.1f}\")" "$stem")
  design="bore_${fam}_${kg}kg"
  "$PY" prototypes/first_loop/propose.py "$design" --run "$stem" > "data/first_loop/propose_${design}.log" 2>&1
  echo "$(date '+%H:%M') ${design}: judged, exit $?" >> "$SUMMARY"
done
echo "$(date '+%H:%M') the bore experiment done" >> "$SUMMARY"
