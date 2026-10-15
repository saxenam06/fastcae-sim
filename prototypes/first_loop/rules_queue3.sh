#!/usr/bin/env bash
# PROTOTYPE (LOP-28) - production's thin, spaced members tried where they have room (rule3_thin stalled at the least mass,
# 13 October 02:25): rule3b_thin, the stiffest housing at a fixed 7.2 kg (compliance with every tilt and bed held at 1/1.25,
# the intermediate seat at 1/1.4) with members at most 8 mm wide and 20 mm apart in plan (`topo.plan_share`'s mask), the
# protected interfaces, the brackets' floors and the one-way curvature everywhere; drawn in the field. Waits for final1.
# Run: bash prototypes/first_loop/rules_queue3.sh
set -u
cd "$(dirname "$0")/../.."
OUTD=data/first_loop
until grep -qE "proposed in|FAILED|failed" "$OUTD/propose_final1.out" 2> /dev/null || [ -f "$OUTD/memory_guard_final1.stopped" ]; do sleep 10; done
until [ -f "$OUTD/look_face_final1.png" ] || grep -q FAILED "$OUTD/propose_final1.out"; do sleep 5; done
sleep 5
export GUARD_FLOOR=600 GUARD_STRIKES=4 LOOP_EXACT_WALLS=1 LOOP_SAFETY_SEATS="intermediate -z=1.4"
bash prototypes/first_loop/campaign_run.sh rule3b_thin --budget 7.2 --voxel 4 -- --max-member 0 --band 24 --height-field 6 --safety 1.25 \
  --empty --protect --brackets floors:51.8,64.7,50.6 --bending dev1_regions.npz --plan-gap 20 --plan-width 8
echo "rule3b done"
