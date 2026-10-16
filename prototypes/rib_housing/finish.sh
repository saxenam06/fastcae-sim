#!/usr/bin/env bash
# The housing's workflow after the optimisation, one stage at a time (LOP-34; a prototype):
# `finish.sh <label> [<optimiser pid>]` waits for `optimise.py <label>` to end, then draws it and
# checks its FE surfaces (`draw_check.sh`), judges it (`judge_bg.sh`: oil-tight, FE on the CPU,
# castability, grade, pictures), judges the reference `baseline2_lw8_smooth` the same way if it has
# no FE result yet (data/rib_housing/ref), and puts both on one sheet (`sheet_<label>.png`). One
# heavy job at a time; its own log in data/rib_housing/finish_<label>.log, last line `DONE`.
# Start it detached (`setsid nohup`): a restart of the session's worker ends its children.
set -u
label="$1"
pid="${2:-}"
root="$(cd "$(dirname "$0")/../.." && pwd)"
out="$root/data/rib_housing"
py="${LOOP_PY:-$root/.venv/bin/python}"
export LOOP_PY="$py"
log="$out/finish_$label.log"
design="rib_$label"
say() { echo "[$(date -u +%H:%M:%S)] $*" >> "$log"; }
if [ -n "$pid" ]; then
  while kill -0 "$pid" 2>/dev/null; do sleep 20; done
fi
say "the optimisation $label ended: $(grep '^it' "$out/$label.log" | tail -1)"
cd "$root" || exit 1
say "drawing $design and checking its surfaces"
bash prototypes/rib_housing/draw_check.sh "$label" "$design"
say "$(head -2 "$out/draw_check_$design.log" | tr '\n' ' ')"
say "judging $design"
bash prototypes/rib_housing/judge_bg.sh "$label" "$design"
say "judged: $(tail -1 "$out/judge_$label.log"); peak $(cat "$out/judge_$label.peak_mb" 2>/dev/null) MB"
if [ ! -f "$out/ref/fe_baseline2_lw8_smooth.json" ]; then
  say "judging the reference baseline2_lw8_smooth the same way"
  bash prototypes/rib_housing/judge_bg.sh ref baseline2_lw8_smooth --folder="$out/ref" --skip=castable,look
fi
PYTHONPATH="$root/src" "$py" prototypes/rib_housing/sheet.py "sheet_$label.png" \
  "data/rib_housing:$design:the rib-direction field ($design), drawn by the product's drawing" \
  "data/rib_housing/ref:baseline2_lw8_smooth:the reference: the final recipe's baseline2_lw8_smooth, judged the same way" >> "$log" 2>&1
say "DONE"
