#!/usr/bin/env bash
# PROTOTYPE (LOP-28) - production's third rule after the first two (`rules_queue.sh`): rule3_thin, members thin and spaced in
# plan (the plan rule, at most 8 mm wide and 20 mm apart, counting only the metal beyond each wall's least height:
# `topo.plan_share`'s mask), P6's set-up with that one change, drawn in the field. Waits for rule2_dev to finish.
# Run: bash prototypes/first_loop/rules_queue2.sh
set -u
cd "$(dirname "$0")/../.."
OUTD=data/first_loop
until grep -qE "proposed in|FAILED|failed" "$OUTD/propose_rule2_dev.out" 2> /dev/null || [ -f "$OUTD/memory_guard_rule2_dev.stopped" ]; do sleep 10; done
until [ -f "$OUTD/look_face_rule2_dev.png" ] || grep -q FAILED "$OUTD/propose_rule2_dev.out"; do sleep 5; done
sleep 5
export GUARD_FLOOR=600 GUARD_STRIKES=4 LOOP_EXACT_WALLS=1 LOOP_SAFETY_SEATS="intermediate -z=1.4"
bash prototypes/first_loop/campaign_run.sh rule3_thin --budget 7.0 --voxel 4 -- --max-member 0 --band 24 --height-field 6 --safety 1.25 \
  --empty --protect --brackets floors:51.8,64.7,50.6 --objective mass_tilt --plan-gap 20 --plan-width 8
echo "rule3 done"
