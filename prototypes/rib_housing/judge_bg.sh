#!/usr/bin/env bash
# One design's judgement in the background (LOP-34; a prototype): `judge_bg.sh <name> <design>
# [judge.py's options]` runs `judge.py` from data/rib_housing/fe_cwd (TetGen writes its dumps in the
# working folder), logs to data/rib_housing/judge_<name>.log (its last line `EXIT <code>`) and the
# host's peak memory in use (MB) to judge_<name>.peak_mb.
set -u
name="$1"; shift
root="$(cd "$(dirname "$0")/../.." && pwd)"
out="$root/data/rib_housing"
py="${LOOP_PY:-$root/.venv/bin/python}"
mkdir -p "$out/fe_cwd"
log="$out/judge_$name.log"
peak="$out/judge_$name.peak_mb"
rm -f "$peak"
(
  cd "$out/fe_cwd" || exit 1
  PYTHONPATH="$root/checks/support/gpu_on_cpu:$root/src:$root/prototypes/rib_housing" PYTHONUNBUFFERED=1 \
    "$py" "$root/prototypes/rib_housing/judge.py" "$@" > "$log" 2>&1
  echo "EXIT $?" >> "$log"
) &
job=$!
top=0
while kill -0 "$job" 2>/dev/null; do
  used=$(free -m | awk 'NR==2{print $3}')
  if [ "$used" -gt "$top" ]; then top=$used; echo "$top" > "$peak"; fi
  sleep 3
done
