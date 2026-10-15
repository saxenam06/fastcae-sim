#!/usr/bin/env bash
# The housing's workflow after the optimisation, one stage at a time (LOP-34; a prototype):
# `finish.sh <label> [<voxel mm>]` waits for `optimise.py <label>` to end (its pid in
# data/rib_housing/<label>.pid), then draws it (`drawrib.py`), pictures its plan, judges it
# (`judge.py`: oil-tight, FE on the CPU, castability, grade, pictures), judges the reference
# `baseline2_lw8_smooth` the same way (data/rib_housing/ref), and puts both on one sheet.
# One heavy job at a time; each stage's log in data/rib_housing/finish_<label>.log.
set -u
label="$1"
voxel="${2:-4}"
root="$(cd "$(dirname "$0")/../.." && pwd)"
out="$root/data/rib_housing"
py="${LOOP_PY:-$root/.venv/bin/python}"
export PYTHONPATH="$root/checks/support/gpu_on_cpu:$root/src"
log="$out/finish_$label.log"
design="rib_$label"
say() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$log"; }
if [ -f "$out/$label.pid" ]; then
  pid="$(cat "$out/$label.pid")"
  while kill -0 "$pid" 2>/dev/null; do sleep 20; done
fi
say "the optimisation $label ended: $(grep '^it' "$out/$label.log" | tail -1)"
cd "$root"
say "drawing $design"
"$py" prototypes/rib_housing/drawrib.py "$label" "$design" --voxel="$voxel" > "$out/draw_$label.log" 2>&1
say "drawn (exit $?): $(grep -E 'kg \(motor side' "$out/draw_$label.log" | tail -1)"
"$py" prototypes/rib_housing/plan_view.py "$design" >> "$log" 2>&1
say "judging $design"
"$py" prototypes/rib_housing/judge.py "$design" > "$out/judge_$design.log" 2>&1
say "judged (exit $?)"
say "judging the reference baseline2_lw8_smooth the same way"
"$py" prototypes/rib_housing/judge.py baseline2_lw8_smooth --folder="$out/ref" > "$out/judge_ref.log" 2>&1
say "judged (exit $?)"
"$py" prototypes/rib_housing/sheet.py "sheet_$label.png" \
  "data/rib_housing:$design:the rib-direction field ($design), drawn by the product's drawing" \
  "data/rib_housing/ref:baseline2_lw8_smooth:the reference: the final recipe's baseline2_lw8_smooth, judged the same way" >> "$log" 2>&1
say "DONE"
