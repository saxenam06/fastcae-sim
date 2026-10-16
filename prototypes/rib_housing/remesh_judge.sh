#!/usr/bin/env bash
# A run drawn, remeshed at FE's scale and judged (LOP-34; a prototype): `remesh_judge.sh <label>
# <design> [<edge mm>]` draws `optimise.py <label>`'s state as <design> (`drawrib.py`), its plan
# reading, remeshes it as <design>r (`remesh.py`, 6 mm by default), checks the remeshed halves for
# self-crossings, judges <design>r with FE's decimation bypassed (`judge_bg.sh ... --no-coarse`:
# oil-tight, FE, castability, grade, pictures) and puts it on a sheet beside the reference. Its log is
# data/rib_housing/remesh_judge_<design>.log, last line `DONE`. Start it detached (`setsid nohup`).
set -u
label="$1"; design="$2"; edge="${3:-6}"
root="$(cd "$(dirname "$0")/../.." && pwd)"
out="$root/data/rib_housing"
py="${LOOP_PY:-$root/.venv/bin/python}"
export LOOP_PY="$py"
log="$out/remesh_judge_$design.log"
say() { echo "[$(date -u +%H:%M:%S)] $*" >> "$log"; }
cd "$root" || exit 1
mkdir -p "$out/fe_cwd"
: > "$log"
say "drawing $design from $label"
PYTHONPATH="$root/checks/support/gpu_on_cpu:$root/src" "$py" prototypes/rib_housing/drawrib.py "$label" "$design" > "$out/draw_$design.log" 2>&1
say "drawn (exit $?): $(grep -E 'kg \(motor side' "$out/draw_$design.log" | tail -1)"
grep -E "holds [0-9]+ of the layout" "$out/draw_$design.log" >> "$log"
PYTHONPATH="$root/src" "$py" prototypes/rib_housing/plan_view.py "$design" >> "$log" 2>&1
say "remeshing at $edge mm"
PYTHONPATH="$root/src" "$py" prototypes/rib_housing/remesh.py "$design" "${design}r" "$edge" 2>&1 | grep -E "triangles" >> "$log"
for half in motor_side cover; do
  PYTHONPATH="$root/src" "$py" -c "
from zenryx.domains.gearbox.housing import mesh as mr
tm = mr.load('$out/${design}r_$half.stl')
print('$half: ' + str(len(tm.faces)) + ' faces, ' + str(len(mr.crossing_centres(tm.vertices, tm.faces))) + ' crossing')
" 2>&1 | tail -1 >> "$log"
done
say "judging ${design}r (FE's decimation bypassed)"
bash prototypes/rib_housing/judge_bg.sh "${design}r" "${design}r" --no-coarse
say "judged: $(tail -1 "$out/judge_${design}r.log"); peak $(cat "$out/judge_${design}r.peak_mb" 2>/dev/null) MB"
PYTHONPATH="$root/src" "$py" prototypes/rib_housing/sheet.py "sheet_$design.png" \
  "data/rib_housing:${design}r:the rib-direction field ($design, remeshed at $edge mm for FE)" \
  "data/rib_housing/ref:baseline2_lw8_smooth:the reference: the final recipe's baseline2_lw8_smooth, judged the same way" >> "$log" 2>&1
say "DONE"
