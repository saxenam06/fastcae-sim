#!/usr/bin/env bash
# PROTOTYPE (LOP-27) - the junction cases on the empty start (the engineer, 12 October 23:05: "try"), one at a time,
# each the baseline's settings (empty1_5.5kg: 4 mm, 5.5 kg, peak drive, the factor 1.15, the 24 mm band, plan
# smoothing 6 mm) with one change, through propose.py (drawing, the oil-tight gate, FE, castability, the grade), then
# its pictures along the pull:
#   case1  the least metal: every bearing line held, the metal the least (mass_tilt; the beds' factor 1.5, as the
#          lean run of 11 October that passed); is the blobs' metal needed?
#   case2  the greatest member: no member thicker than 12 mm anywhere (--max-member 12, read near its worst ball,
#          LOOP_MEMBER_P=40)
#   case3  one junction a clean form: the cover's patch between the intermediate and output bearings one flat web
#          (--height-volumes junction_web1_cols.npz, made by web_form.py)
#   junction_cases.sh "case1 case2 case3"   (each case's log: data/first_loop/propose_<design>.out)
set -u
cd "$(dirname "$0")/../.."
PY=.venv/Scripts/python.exe
CASES=${1:-"case1 case2 case3"}
BASE=(--max-member 0 --band 24 --height-field 6 --safety 1.15 --empty)
for c in $CASES; do
  case $c in
    case1) d=case1_least_5.5kg; extra=(--objective mass_tilt --safety-beds 1.5); envs=() ;;
    case2) d=case2_max12_5.5kg; extra=(--max-member 12); envs=(LOOP_MEMBER_P=40) ;;
    case3) d=case3_web_5.5kg; extra=(--height-volumes junction_web1_cols.npz); envs=() ;;
    *) echo "unknown case $c"; continue ;;
  esac
  echo "== $c $d $(date +%H:%M:%S)"
  env "${envs[@]}" "$PY" prototypes/first_loop/propose.py "$d" --budget 5.5 --voxel 4 -- "${BASE[@]}" "${extra[@]}" > "data/first_loop/propose_$d.out" 2>&1
  tail -1 "data/first_loop/propose_$d.out"
  "$PY" prototypes/first_loop/look.py "$d" face > "data/first_loop/look_face_$d.log" 2>&1
done
echo "done $(date +%H:%M:%S)"
