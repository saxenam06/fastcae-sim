#!/usr/bin/env bash
# One drawn design judged, then put on a sheet beside the reference (LOP-34; a prototype):
# `judge_sheet.sh <design> [judge.py's options]`; its log data/rib_housing/judge_sheet_<design>.log,
# last line `DONE`. Start it detached (`setsid nohup`).
set -u
design="$1"; shift
root="$(cd "$(dirname "$0")/../.." && pwd)"
out="$root/data/rib_housing"
py="${LOOP_PY:-$root/.venv/bin/python}"
export LOOP_PY="$py"
log="$out/judge_sheet_$design.log"
say() { echo "[$(date -u +%H:%M:%S)] $*" >> "$log"; }
cd "$root" || exit 1
: > "$log"
say "judging $design"
bash prototypes/rib_housing/judge_bg.sh "$design" "$design" "$@"
say "judged: $(tail -1 "$out/judge_$design.log"); peak $(cat "$out/judge_$design.peak_mb" 2>/dev/null) MB"
PYTHONPATH="$root/src" "$py" prototypes/rib_housing/sheet.py "sheet_$design.png" \
  "data/rib_housing:$design:the rib-direction field ($design), drawn by the product's drawing" \
  "data/rib_housing/ref:baseline2_lw8_smooth:the reference: the final recipe's baseline2_lw8_smooth, judged the same way" >> "$log" 2>&1
say "DONE"
