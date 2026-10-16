#!/usr/bin/env bash
# Draw a state and check its FE surfaces before judging (LOP-34; a prototype):
# `draw_check.sh <label> <design>` runs `drawrib.py <label> <design>`, its plan reading, then
# `crossings.py` on each half at FE's 7 mm and at the next rung (7.49 mm); everything to
# data/rib_housing/draw_check_<design>.log, its last line `DONE`.
set -u
label="$1"; design="$2"
root="$(cd "$(dirname "$0")/../.." && pwd)"
out="$root/data/rib_housing"
py="${LOOP_PY:-$root/.venv/bin/python}"
log="$out/draw_check_$design.log"
export PYTHONPATH="$root/checks/support/gpu_on_cpu:$root/src"
cd "$root" || exit 1
mkdir -p "$out/fe_cwd"
"$py" prototypes/rib_housing/drawrib.py "$label" "$design" > "$out/draw_$design.log" 2>&1
echo "drawn (exit $?): $(grep -E 'kg \(motor side' "$out/draw_$design.log" | tail -1)" > "$log"
grep -E "holds [0-9]+ of the layout" "$out/draw_$design.log" >> "$log"
"$py" prototypes/rib_housing/plan_view.py "$design" >> "$log" 2>&1
for half in motor_side cover; do
  "$py" prototypes/rib_housing/self_cross.py "$design" "$half" 7 --first-round 2>&1 | grep -vE "Warning|warn" | tail -8 >> "$log"
  for edge in 7 7.49; do
    "$py" prototypes/rib_housing/crossings.py "$design" "$half" "$edge" 2>&1 | grep -vE "Warning|warn" | tail -4 >> "$log"
  done
done
echo DONE >> "$log"
