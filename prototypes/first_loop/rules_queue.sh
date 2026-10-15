#!/usr/bin/env bash
# PROTOTYPE (LOP-28) - production's rules tried one at a time on the protected least-mass set-up (the engineer, 13 October
# 01:54: "what are those basic rules which they follow, which ours are not following... if you constrain, then it starts
# creating clean patterns"): after the run named first has finished, the plain walls' derivative check, then
#   rule1_wall  the walls plain (LOOP_WALL_GATE: a wall bare or carrying a member at least 6 mm tall),
#   rule2_dev   every surface curving one way at most (the double curvature everywhere at half the reference's),
# each P6's set-up with one change, drawn in the field (LOOP_EXACT_WALLS=1). One heavy job at a time.
# Run: bash prototypes/first_loop/rules_queue.sh <design to wait for>
set -u
cd "$(dirname "$0")/../.."
OUTD=data/first_loop
WAIT="$1"
until grep -qE "proposed in|FAILED|failed" "$OUTD/propose_$WAIT.out" 2> /dev/null || [ -f "$OUTD/memory_guard_$WAIT.stopped" ]; do sleep 10; done
until [ -f "$OUTD/look_face_$WAIT.png" ] || grep -q FAILED "$OUTD/propose_$WAIT.out"; do sleep 5; done
sleep 5
COMMON=(--budget 7.0 --voxel 4 -- --max-member 0 --band 24 --height-field 6 --safety 1.25 --empty --protect --brackets floors:51.8,64.7,50.6 --objective mass_tilt)
export GUARD_FLOOR=600 GUARD_STRIKES=4 LOOP_EXACT_WALLS=1 LOOP_SAFETY_SEATS="intermediate -z=1.4"
LOOP_WALL_GATE=6 .venv/Scripts/python.exe prototypes/first_loop/topo_gradcheck.py 10 4 2 --empty > "$OUTD/gradcheck_wallgate.log" 2>&1
tail -1 "$OUTD/gradcheck_wallgate.log"
LOOP_WALL_GATE=6 bash prototypes/first_loop/campaign_run.sh rule1_wall "${COMMON[@]}"
bash prototypes/first_loop/campaign_run.sh rule2_dev "${COMMON[@]}" --bending dev1_regions.npz
echo "rules done"
