#!/usr/bin/env bash
# PROTOTYPE (LOP-32) - the members' fairing stage (the engineer, 15 October 16:10: "Reward. add rules"): the final recipe's
# optimisation settings (recipes/final.json) started from a converged run's field at its own sharpness, with the fairing rules
# (`member_fair`, `topo_free.py --fair`) and the topology frozen; then the final recipe's drawing, FE, castability, the grade
# and the Designs tab's records, as the final workflow (`python -m zenryx.workflow.run`) runs them.
# Run: bash prototypes/first_loop/fair_run.sh <design> <start run stem> [targets, default 0.06:1.0:0.3] [beta, default 16]
set -u
cd "$(dirname "$0")/../.."
d="$1"
start="$2"
targets="${3:-0.06:1.0:0.3}"
beta="${4:-16}"
export LOOP_MEMBER_P=40 LOOP_EXACT_WALLS=1 LOOP_LEAST_MEMBER=8 LOOP_CAST_AFTER=1 GUARD_FLOOR=600 GUARD_STRIKES=4
export LOOP_VOXEL_SMOOTH=3 LOOP_DRAW_SMOOTH=6 LOOP_DRAW_SMOOTH_RANGE=15 LOOP_DRAW_FINE=1
echo "[$(date +%H:%M:%S)] $d: the fairing stage from $start, targets $targets, beta $beta"
bash prototypes/first_loop/campaign_run.sh "$d" --budget 7.73 --voxel 4 -- --max-member 16 --band 24 --height-field 4 --empty \
  --protect --shell-fixed --no-towers --objective mass_tilt --safety 1.5 --modes 0.12 --first-mode 500 --least-width 8 \
  --start "$start" --beta0 "$beta" --beta-most "$beta" --ramp 0 --fair "$targets"
echo "[$(date +%H:%M:%S)] $d done"
