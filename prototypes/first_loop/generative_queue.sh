#!/usr/bin/env bash
# LOP-17: the generative campaign of 10 October (after Virostko et al. 2026): the honest model
# (one cup per half, bolted halves, 4 mm skin, GCMMA on every seat's misalignment), the route and
# the mass as the design variables. One run at a time on the GPU.
# - It first waits for a run already going (its pid as $1, if given).
# - Before each run it waits while data/first_loop/gpu_hold exists: the main session's fe.py
#   runs take the GPU then, never beside an optimisation (one heavy job at a time).
# - Each run's log ends with an "exit N" line; the queue's own log says when each started.
cd "$(dirname "$0")/../.." || exit 1
queue=data/first_loop/generative_queue.log
if [ -n "$1" ]; then
  echo "$(date '+%F %T') waiting for the running pid $1" >> "$queue"
  while tasklist //FI "PID eq $1" 2>/dev/null | grep -q "$1"; do sleep 30; done
  echo "$(date '+%F %T') pid $1 ended" >> "$queue"
fi
for spec in "split 7.73" "split 9" "free 7.73"; do
  set -- $spec
  route=$1; budget=$2
  while [ -f data/first_loop/gpu_hold ]; do sleep 20; done
  log=data/first_loop/generative_${route}_${budget}kg.log
  echo "$(date '+%F %T') start ${route} ${budget} kg -> ${log}" >> "$queue"
  for attempt in 1 2; do
    .venv/Scripts/python.exe prototypes/first_loop/topo_free.py "$budget" 6 200 --route "$route" > "$log" 2>&1
    code=$?
    echo "exit $code" >> "$log"
    [ "$code" -ne 127 ] && break  # 127: a launch that never started (CLAUDE.md), once more
  done
  echo "$(date '+%F %T') end ${route} ${budget} kg, exit ${code}" >> "$queue"
done
echo "$(date '+%F %T') queue done" >> "$queue"
