#!/usr/bin/env bash
# PROTOTYPE (LOP-28) - design moves on the last clashing mode (final2: mode 8 at 2440 Hz, 15 Hz inside s1's band; the
# cover's spokes 12 -> 14 mm left it where it was): three variants of final2, each judged by FE, one at a time:
#   final4  the spokes on both halves (the motor side's input bore carries 21 % of the mode),
#   final5  a lighter housing (every line at 1/1.2, the intermediate seat still at 1/1.5),
#   final6  mount-3's bracket at least 70 cm³ (the bracket carries 11 % of the mode).
# Run: bash prototypes/first_loop/mode_queue.sh
set -u
cd "$(dirname "$0")/../.."
export GUARD_FLOOR=600 GUARD_STRIKES=4 LOOP_EXACT_WALLS=1 LOOP_SAFETY_SEATS="intermediate -z=1.5" LOOP_PANEL_SPOKES="30:6:12"
BASE=(--voxel 4 -- --max-member 0 --band 24 --height-field 6 --empty --protect --objective mass_tilt)
LOOP_SPOKE_HALVES="cover,motor_side" bash prototypes/first_loop/campaign_run.sh final4 --budget 7.4 "${BASE[@]}" --safety 1.25 --brackets floors:51.8,64.7,50.6
LOOP_SPOKE_HALVES="cover" bash prototypes/first_loop/campaign_run.sh final5 --budget 7.3 "${BASE[@]}" --safety 1.2 --brackets floors:51.8,64.7,50.6
LOOP_SPOKE_HALVES="cover" bash prototypes/first_loop/campaign_run.sh final6 --budget 7.3 "${BASE[@]}" --safety 1.25 --brackets floors:51.8,64.7,70
echo "modes queue done"
