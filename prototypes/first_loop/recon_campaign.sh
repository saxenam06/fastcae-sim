#!/usr/bin/env bash
# Approach 2's first experiment (LOP-25; the engineer's plan, `zenryx_new_plan.md` §8): a deliberately diverse
# population of candidates from the same structural evidence (the benchmark's field, `it1_free_5.5kg`: the free
# run at 5.5 kg), each drawn, checked and judged by FE through `propose.py`, one heavy job at a time:
#   A (surface reconstruction): the field's surface smoothed by its signed distance over 3 and 6 mm, Taubin-smoothed;
#   B (skeleton members): the field's members rebuilt along their skeleton, the widths their own, capped at 16 and 12 mm;
#   C (free-form evolution by re-optimisation): the broadest overfilled patch taken out (redistribute), a longer and a
#     shorter length scale (the plan smoothing 10 and 4 mm), another start (the 7.5 kg field), and C1's field drawn by B.
#   recon_campaign.sh ["<candidate> ..."]   (default: all)
# A line a step in data/first_loop/recon_campaign.log. Calls the venv's python directly (concurrent `uv run` exits 127).
set -u
cd "$(dirname "$0")/../.."
PY=.venv/Scripts/python.exe
BENCH=topofree_compliance_tilt_5.5kg_4mm_projected_band24_cup_bolts_split_contract_drive_hfsf_4mm_5.5kg_r6_hf6_single_flange_beds_sf1.15
START=topofree_compliance_tilt_7.5kg_4mm_projected_band24_cup_bolts_split_contract_drive_hfsf_4mm_7.5kg_r6_hf6_single_flange_beds_sf1.15
OPT=(5.5 4 200 --objective compliance_tilt --beds --cases "peak drive" --route split --settle 0.02 --every 25 --beta-most 32 --fast --max-member 0 --band 24 --safety 1.15)
LOG=data/first_loop/recon_campaign.log
ALL="recA1_sdf3 recA2_sdf6 recA3_taubin recB1_skeleton recB2_skel16 recB3_skel12 recC1_redistribute recC2_hf10 recC3_hf4 recC4_start recC5_c1skel"
WANT=${1:-$ALL}

judge() {  # judge <design> <run> [env...]: the drawing, FE, castability, the grade, the pictures, the UI's records
  local d=$1 run=$2
  shift 2
  env "$@" "$PY" prototypes/first_loop/propose.py "$d" --run "$run" > "data/first_loop/propose_$d.log" 2>&1
  local code=$?
  echo "$(date '+%H:%M') $d judged (exit $code): $(tail -1 "data/first_loop/propose_$d.log" | cut -c1-160)" >> "$LOG"
}

optimise() {  # optimise <tag> [topo_free args...]: echoes the run's stem
  local tag=$1
  shift
  "$PY" prototypes/first_loop/topo_free.py "${OPT[@]}" --tag "$tag" "$@" > "data/first_loop/optimise_$tag.log" 2>&1
  grep -a "done in" "data/first_loop/optimise_$tag.log" | tail -1 | sed 's/.*; //'
}

echo "$(date '+%H:%M') approach 2's population: $WANT" >> "$LOG"
for c in $WANT; do
  case $c in
    recA1_sdf3) judge "$c" "$BENCH" LOOP_SDF=3 ;;
    recA2_sdf6) judge "$c" "$BENCH" LOOP_SDF=6 ;;
    recA3_taubin) judge "$c" "$BENCH" LOOP_SMOOTH=20 ;;
    recB1_skeleton) judge "$c" "$BENCH" LOOP_SKELETON=1.0:20:0 ;;
    recB2_skel16) judge "$c" "$BENCH" LOOP_SKELETON=1.0:20:16 ;;
    recB3_skel12) judge "$c" "$BENCH" LOOP_SKELETON=0.8:30:12 ;;
    recC1_redistribute)
      "$PY" prototypes/first_loop/redistribute.py "$BENCH" --label recC1_patch > data/first_loop/redistribute_recC1.log 2>&1
      s=$(optimise recC1 --height-field 6 --space recC1_patch.npz)
      echo "$(date '+%H:%M') recC1 optimised: $s" >> "$LOG"
      [ -n "$s" ] && judge "$c" "$s" && echo "$s" > data/first_loop/recC1_run.txt ;;
    recC2_hf10) s=$(optimise recC2 --height-field 10); echo "$(date '+%H:%M') recC2 optimised: $s" >> "$LOG"; [ -n "$s" ] && judge "$c" "$s" ;;
    recC3_hf4) s=$(optimise recC3 --height-field 4); echo "$(date '+%H:%M') recC3 optimised: $s" >> "$LOG"; [ -n "$s" ] && judge "$c" "$s" ;;
    recC4_start) s=$(optimise recC4 --height-field 6 --start "$START" --beta0 4); echo "$(date '+%H:%M') recC4 optimised: $s" >> "$LOG"; [ -n "$s" ] && judge "$c" "$s" ;;
    recC5_c1skel) [ -f data/first_loop/recC1_run.txt ] && judge "$c" "$(cat data/first_loop/recC1_run.txt)" LOOP_SKELETON=1.0:20:16 ;;
  esac
done
echo "$(date '+%H:%M') approach 2's population done" >> "$LOG"
