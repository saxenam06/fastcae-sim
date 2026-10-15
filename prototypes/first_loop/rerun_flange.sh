#!/usr/bin/env bash
# PROTOTYPE (LOP-20) - the method on the set-up of 11 October (the contract's split flange held
# fixed, the split on a voxel face, the fixed voxels at the exact fixed metal's mass; `topo_free.
# build_free`'s `flange`), at the reference's whole 7.73 kg: the stiff design, then every bearing's
# tilt held from it, then the outcome drawn and judged. Peak drive alone (the engineer, 10 October
# 14:54 and 11 October 00:46) and one design, not three (11 October 00:54: the thinned and
# thickened versions only proved their worth on the tilt objective, and cost three solves a step);
# each stage stops once its result has settled (`topo.SETTLE_STOP`).
# Logs: data/first_loop/run_flange_stiff.log, run_flange_tilt.log, chain_<design>.log.
cd "$(dirname "$0")/../.." || exit 1
PY=.venv/Scripts/python.exe
LOG=data/first_loop
DESIGN=${1:-outcome_skin_6mm_drive}
COMMON="--route split --settle 0.02 --every 25 --beta-most 32 --fast --max-member 12"
STIFF=topofree_compliance_gcmma_7.73kg_6mm_projected_cup_bolts_skin4_split_contract_drive_single_max12_flange
TILT=topofree_compliance_tilt_7.73kg_6mm_projected_cup_bolts_skin4_split_contract_drive_single_max12_flange
# shellcheck disable=SC2086
$PY prototypes/first_loop/topo_free.py 7.73 6 200 --objective compliance_gcmma --cases "peak drive" $COMMON \
  > $LOG/run_flange_stiff.log 2>&1 || { echo "the stiff run failed ($?)"; exit 1; }
# shellcheck disable=SC2086
$PY prototypes/first_loop/topo_free.py 7.73 6 140 --objective compliance_tilt --cases "peak drive" $COMMON \
  --start $STIFF --beta0 8 --ramp 0 > $LOG/run_flange_tilt.log 2>&1 || { echo "the tilt run failed ($?)"; exit 1; }
bash prototypes/first_loop/outcome_chain.sh $TILT "$DESIGN" skin
$PY prototypes/first_loop/names.py > $LOG/names_${DESIGN}.log 2>&1
echo "done: $TILT drawn as $DESIGN"
