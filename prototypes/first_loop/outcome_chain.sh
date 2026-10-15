#!/usr/bin/env bash
# LOP-17: once an optimisation has written its field, draw its outcome as CAD and judge it, then
# give the GPU back to the campaign's queue.
#   outcome_chain.sh <run stem> <design stem> [organic|relief|skin]
# Waits for data/first_loop/<run stem>.npz; then outcome_cad.py (in the drawing named, organic by
# default; skin: LOP-20), castable.py, fe.py (8 mm), grade.py, look.py (the organic shape's and
# the CAD's), view_export.py and topo_export.py, each logged under data/first_loop/; then
# removes data/first_loop/gpu_hold, so the queue's next run starts. A step that fails is said in
# the chain's log and the next steps that need it are skipped; the hold is removed either way.
cd "$(dirname "$0")/../.." || exit 1
run=$1; design=$2; form=${3:-organic}
log=data/first_loop/chain_${design}.log
py=.venv/Scripts/python.exe
echo "$(date '+%F %T') waiting for ${run}.npz" >> "$log"
while [ ! -f "data/first_loop/${run}.npz" ]; do sleep 20; done
sleep 5  # let the run finish writing its record and picture
echo "$(date '+%F %T') ${run}.npz is there" >> "$log"
step() {  # step <name> <command...>: run it, log its exit
  local name=$1; shift
  echo "$(date '+%F %T') ${name}: start" >> "$log"
  "$@" > "data/first_loop/${name}_${design}.log" 2>&1
  local code=$?
  echo "$(date '+%F %T') ${name}: exit ${code}" >> "$log"
  return $code
}
if step build "$py" prototypes/first_loop/outcome_cad.py "$run" "$design" "$form"; then
  step view_organic "$py" prototypes/first_loop/view_export.py "${design}_organic"  # the organic shape alone, on the Designs page first
  step look_organic "$py" prototypes/first_loop/look.py "${design}_organic"
  step castable "$py" prototypes/first_loop/castable.py "$design"
  step look "$py" prototypes/first_loop/look.py "$design"
  if step fe "$py" prototypes/first_loop/fe.py "$design" 8.0; then
    step grade "$py" prototypes/first_loop/grade.py
  fi
  step view "$py" prototypes/first_loop/view_export.py "$design"
fi
step topo_export "$py" prototypes/first_loop/topo_export.py "$run"
rm -f data/first_loop/gpu_hold
echo "$(date '+%F %T') done; the GPU hold removed" >> "$log"
