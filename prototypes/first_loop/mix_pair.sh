#!/usr/bin/env bash
# PROTOTYPE (LOP-29) - the baseline with and without the optimiser's plan mixing (the engineer, 13 October 22:40: "I would
# like to see the result without this averaging and with this averaging of 6 mm. Two runs for that"). One after the other,
# each a proposal under the memory guard (`campaign_run.sh`), FE before castability (`LOOP_CAST_AFTER=1`).
# The baseline (the engineer's, 22:21-22:58): the empty start; the protected interfaces; the 4 mm shell protected
# (`--shell-fixed`) and only members on it (`LOOP_LEAST_MEMBER=8`: a column counts once it stands 8 mm proud); the set-up
# keeps clear what the drawing keeps clear; the least metal under 7.73 kg; every tilt and bed at 1/1.25, every seat alike;
# the modes 12 % clear of each gear order; no section much over 16 mm (read at p 40); peak drive; the drawing keeps every
# cube, walls exact. The couplings rigid in the optimiser and FE alike (`couplings.py`; the engineer, 22:40-22:47).
# No bearing towers (`--no-towers`; the engineer, 13 October 23:49): the fixed shell keeps the floors flat, the optimiser
# builds each boss on its seat's 4 mm ring.
# `--height-field 6` mixes each column's height with its neighbours' within 6 mm; `--height-field 4` reaches none of them.
set -u
cd "$(dirname "$0")/../.."
export LOOP_MEMBER_P=40 GUARD_FLOOR=600 GUARD_STRIKES=4 LOOP_EXACT_WALLS=1 LOOP_CAST_AFTER=1 LOOP_LEAST_MEMBER=8
for spec in "baseline1:6" "baseline2:4"; do
  d="${spec%%:*}"
  r="${spec##*:}"
  echo "[$(date +%H:%M:%S)] $d (--height-field $r)"
  bash prototypes/first_loop/campaign_run.sh "$d" --budget 7.73 --voxel 4 -- --max-member 16 --band 24 --height-field "$r" --empty --protect \
    --shell-fixed --no-towers --objective mass_tilt --safety 1.25 --modes 0.12
done
echo "[$(date +%H:%M:%S)] both done"
