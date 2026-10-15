#!/usr/bin/env bash
# PROTOTYPE (LOP-23) - the height envelope's sweep: one design proposal (propose.py, flow B) for each
# entry, one at a time. Production's ribs stand 10-25 mm off their shell
# (docs/research/2026-10-11-production-ev-housings-against-the-ribbed-cad.md); at 7.73 kg an 18 mm
# band filled nearly whole, so the budget comes down until the members part into ribs.
#
# Run: bash prototypes/first_loop/envelope_sweep.sh "6.0:18 6.5:18 6.0:20:4:--max-member+8 6.0:20:4:--ribs+--max-member+0"
#      Each entry is budget:band[:voxel[:extra topo_free.py arguments, '+' for a space]]; its design is
#      outcome_env<band>_<budget>kg (6 mm voxels), outcome_env<band>_<voxel>mm_<budget>kg, or with
#      --ribs outcome_ribs<band>_<voxel>mm_<budget>kg.
set -u
cd "$(dirname "$0")/../.."
PY=.venv/Scripts/python.exe
for entry in ${1:-"6.0:18 6.5:18 7.0:18"}; do
    IFS=: read -r budget band voxel extra <<< "$entry"
    voxel=${voxel:-6}
    extra=${extra//+/ }
    kind=env
    case " $extra " in *" --ribs-from "*) kind=ribsfield ;; *" --ribs "*) kind=ribs ;; esac
    case " $extra " in *" --fins "*) if [ "$kind" = env ]; then kind=ribsfins; else kind="${kind}fins"; fi ;; esac
    case " $extra " in *" --rib-filter "*) kind="${kind}uni" ;; esac
    if [ "$voxel" = "6" ]; then design="outcome_${kind}${band}_${budget}kg"; else design="outcome_${kind}${band}_${voxel}mm_${budget}kg"; fi
    while [ -e data/first_loop/gpu_hold ]; do sleep 20; done
    for attempt in 1 2 3; do
        start=$(date +%s)
        # shellcheck disable=SC2086 # extra is the arguments, split on purpose
        "$PY" prototypes/first_loop/propose.py "$design" --budget "$budget" --voxel "$voxel" -- --band "$band" $extra > "data/first_loop/propose_${design}.log" 2>&1
        code=$?
        # a start that failed within seconds (concurrent launches exit 127 at random) is retried; a
        # stage that failed later is not
        if [ "$code" -ne 127 ] || [ $(( $(date +%s) - start )) -gt 20 ]; then break; fi
        sleep 5
    done
    echo "$(date +%H:%M:%S) $design exit $code: $(tail -1 "data/first_loop/propose_${design}.log")"
done
