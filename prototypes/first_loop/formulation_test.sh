#!/usr/bin/env bash
# PROTOTYPE (LOP-20) - which formulation, on the set-up of 11 October (peak drive alone, one design,
# each run stopping once settled, MMA's dual subproblem): (1) one run, the stiffness the objective,
# every seat's tilt and bearing bed held from iteration 1 (`--beds`); (2) the two stages, the stiff
# design then the tilt held from it, as `rerun_flange.sh`. Compared by their metal-or-air checks
# (compliance, the worst tilt and bed) and their times. Logs: data/first_loop/form_*.log.
cd "$(dirname "$0")/../.." || exit 1
PY=.venv/Scripts/python.exe
LOG=data/first_loop
COMMON="--cases peak\ drive --route split --settle 0.02 --every 25 --beta-most 32 --fast --max-member 12"
# shellcheck disable=SC2086
$PY prototypes/first_loop/topo_free.py 7.73 6 200 --objective compliance_tilt --beds --cases "peak drive" \
  --route split --settle 0.02 --every 25 --beta-most 32 --fast --max-member 12 --tag onerun > $LOG/form_onerun.log 2>&1
$PY prototypes/first_loop/topo_free.py 7.73 6 200 --objective compliance_gcmma --cases "peak drive" \
  --route split --settle 0.02 --every 25 --beta-most 32 --fast --max-member 12 --tag dual > $LOG/form_stiff_dual.log 2>&1
STIFF=topofree_compliance_gcmma_7.73kg_6mm_projected_cup_bolts_skin4_split_contract_drive_dual_single_max12_flange
$PY prototypes/first_loop/topo_free.py 7.73 6 140 --objective compliance_tilt --beds --cases "peak drive" \
  --route split --settle 0.02 --every 25 --beta-most 32 --fast --max-member 12 --tag dual \
  --start $STIFF --beta0 8 --ramp 0 > $LOG/form_tilt_dual.log 2>&1
echo "formulation test done"
