#!/usr/bin/env bash
# PROTOTYPE (LOP-29) - the baseline: only the settings agreed with the engineer (14 October 12:35: no setting added without
# asking; docs/features/loop/2026-10-14-problem-and-approach.md lists them). Baseline 2's set-up (no plan mixing,
# `--height-field 4`; 01:44: "No baseline1 going forward") with the housing's first mode at least 500 Hz on the lowest six modes
# (`--first-mode 500`; 01:17, 02:02, 12:12). The empty start; the 4 mm shell, the sealing land, the bolts' bosses and the mounts'
# lugs fixed, no towers; members only (8 mm proud); the least metal under 7.73 kg, every line at 1/1.5 (12:12); the modes 12 %
# clear of the gear orders; sections at most about 16 mm (p 40); peak drive; rigid couplings; every cube drawn, walls exact; FE
# then castability. Out until the engineer says (12:35): the sharpness cap (`--beta-most 4`), the drawing's Taubin smoothing
# (`LOOP_SMOOTH`) and the kept-clear check's override (`LOOP_KEEP_CLEAR_OK`).
# Run: bash prototypes/first_loop/fm500_run.sh [design name, default baseline2_fm500] [more topo_free.py arguments]
set -u
cd "$(dirname "$0")/../.."
d="${1:-baseline2_fm500}"
shift || true
export LOOP_MEMBER_P=40 GUARD_FLOOR=600 GUARD_STRIKES=4 LOOP_EXACT_WALLS=1 LOOP_CAST_AFTER=1 LOOP_LEAST_MEMBER=8
echo "[$(date +%H:%M:%S)] $d (--height-field 4, --first-mode 500)"
bash prototypes/first_loop/campaign_run.sh "$d" --budget 7.73 --voxel 4 -- --max-member 16 --band 24 --height-field 4 --empty --protect \
  --shell-fixed --no-towers --objective mass_tilt --safety 1.5 --modes 0.12 --first-mode 500 "$@"
echo "[$(date +%H:%M:%S)] $d done"
