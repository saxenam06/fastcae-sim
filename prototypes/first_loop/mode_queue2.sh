#!/usr/bin/env bash
# PROTOTYPE (LOP-28) - the mount-3 bracket as the mode's tuning mass (final6: its floor 50.6 -> 70 cm³ moved mode 8 from 2440
# to 2433 Hz; s1's band ends at 2425): final2's set-up with mount-3's bracket at least 110 cm³ (final7) and 150 cm³ (final8),
# one at a time, each judged by FE.
# Run: bash prototypes/first_loop/mode_queue2.sh
set -u
cd "$(dirname "$0")/../.."
export GUARD_FLOOR=600 GUARD_STRIKES=4 LOOP_EXACT_WALLS=1 LOOP_SAFETY_SEATS="intermediate -z=1.5" LOOP_PANEL_SPOKES="30:6:12" LOOP_SPOKE_HALVES="cover"
BASE=(--budget 7.4 --voxel 4 -- --max-member 0 --band 24 --height-field 6 --empty --protect --objective mass_tilt --safety 1.25)
bash prototypes/first_loop/campaign_run.sh final7 "${BASE[@]}" --brackets floors:51.8,64.7,110
bash prototypes/first_loop/campaign_run.sh final8 "${BASE[@]}" --brackets floors:51.8,64.7,150
echo "modes queue 2 done"
