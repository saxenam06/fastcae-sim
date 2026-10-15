#!/usr/bin/env bash
# PROTOTYPE (LOP-27) - after junction_cases.sh "case1 case2" ends (its log says "done"): case 3 (the cover's patch as one
# flat web), then case 1 again done right: the least metal with the baseline's own factor of safety for the beds
# (1.15; the first case 1 held them at 1.5, two changes at once), one at a time.
set -u
cd "$(dirname "$0")/../.."
PY=.venv/Scripts/python.exe
until grep -q "^done" data/first_loop/junction_cases.log 2>/dev/null; do sleep 20; done
bash prototypes/first_loop/junction_cases.sh "case3"
d=case1b_least_5.5kg
echo "== case1b $d $(date +%H:%M:%S)"
"$PY" prototypes/first_loop/propose.py "$d" --budget 5.5 --voxel 4 -- --max-member 0 --band 24 --height-field 6 --safety 1.15 --empty \
  --objective mass_tilt > "data/first_loop/propose_$d.out" 2>&1
tail -1 "data/first_loop/propose_$d.out"
"$PY" prototypes/first_loop/look.py "$d" face > "data/first_loop/look_face_$d.log" 2>&1
echo "done $(date +%H:%M:%S)"
