#!/usr/bin/env bash
# A walls state drawn, pictured, then judged (LOP-34, the restart; a prototype):
# `draw_judge.sh <label> <design> [--voxel=<mm>] [judge.py's options]`. Draws on the 2 mm grid
# (`RIB_DRAW_FINE`, default 2: FE's mesher refused the 1 mm drawings of the first attempt), pictures
# it, judges it (`prototypes/rib_housing/judge_bg.sh`). Its log data/rib_walls/draw_judge_<design>.log,
# last line `DONE`. Start it detached (`setsid nohup`).
set -u
label="$1"; design="$2"; shift 2
voxel="--voxel=4"
judge_args=()
for a in "$@"; do
  case "$a" in
    --voxel=*) voxel="$a" ;;
    *) judge_args+=("$a") ;;
  esac
done
root="$(cd "$(dirname "$0")/../.." && pwd)"
out="$root/data/rib_walls"
py="${LOOP_PY:-$root/.venv/bin/python}"
export LOOP_PY="$py"
log="$out/draw_judge_$design.log"
say() { echo "[$(date -u +%H:%M:%S)] $*" >> "$log"; }
cd "$root" || exit 1
: > "$log"
say "drawing $label as $design ($voxel)"
RIB_DRAW_FINE="${RIB_DRAW_FINE:-2}" PYTHONPATH="$root/checks/support/gpu_on_cpu:$root/src" \
  "$py" prototypes/rib_walls/drawwall.py "$label" "$design" "$voxel" > "$out/draw_$design.log" 2>&1
say "drawn (exit $?): $(grep -E 'kg \(motor side' "$out/draw_$design.log" | tail -1 | cut -c12-)"
grep -E "holds [0-9,]+ of the run" "$out/draw_$design.log" | cut -c12- >> "$log"
PYTHONPATH="$root/checks/support/gpu_on_cpu:$root/src" "$py" prototypes/rib_walls/pictures.py "$design" 2>&1 | grep png >> "$log"
rm -f "$out"/fe_mesh_"$design"_*.pkl
say "judging"
bash prototypes/rib_housing/judge_bg.sh "$design" "$design" --folder="$out" "${judge_args[@]}"
say "judged: $(tail -1 "$root/data/rib_housing/judge_$design.log"); peak $(cat "$root/data/rib_housing/judge_$design.peak_mb" 2>/dev/null) MB"
grep -E "worst shape|flat tet|unknowns|single factor|refine|Refused|first mode" "$root/data/rib_housing/judge_$design.log" | cut -c1-200 >> "$log"
say "DONE"
