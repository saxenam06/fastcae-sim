#!/usr/bin/env bash
# PROTOTYPE (LOP-28) - production's panel spokes as the design move on the cover's panel mode (13 October 02:33: P6's mode 8 at
# 2498 Hz, s1's 2500, lives on the cover's output and intermediate bores; a floor on their bridge moved it 0.4 %): P6's run
# drawn again with spokes every 30° from each boss across the end walls, 6 mm thick and 10 mm proud (LOOP_PANEL_SPOKES), in the
# field, judged by FE. Waits for rule3b_thin.
# Run: bash prototypes/first_loop/spokes_queue.sh
set -u
cd "$(dirname "$0")/../.."
OUTD=data/first_loop
until grep -qE "proposed in|FAILED|failed" "$OUTD/propose_rule3b_thin.out" 2> /dev/null || [ -f "$OUTD/memory_guard_rule3b_thin.stopped" ]; do sleep 10; done
until [ -f "$OUTD/look_face_rule3b_thin.png" ] || grep -q FAILED "$OUTD/propose_rule3b_thin.out" || [ -f "$OUTD/memory_guard_rule3b_thin.stopped" ]; do sleep 5; done
sleep 5
R6=$(ls "$OUTD" | grep "topofree.*prot6_least.*\.npz$" | grep -v checkpoint | head -1)
export GUARD_FLOOR=600 GUARD_STRIKES=4 LOOP_EXACT_WALLS=1
LOOP_PANEL_SPOKES="30:6:10" bash prototypes/first_loop/campaign_run.sh p6spk --run "${R6%.npz}"
echo "spokes done"
