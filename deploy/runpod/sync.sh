#!/usr/bin/env bash
# PLT-12: move the loop's files between the laptop and the RunPod network volume, through RunPod's S3-compatible API
# (the AWS CLI; no worker started, nothing billed but the volume). From the repository's root, in Git Bash:
#
#   bash deploy/runpod/sync.sh pull [pattern]   # the volume's data/first_loop/ and web/src/records/ to the laptop
#   bash deploy/runpod/sync.sh push [pattern]   # the laptop's data/first_loop/ to the volume (an earlier run to redraw)
#
# pattern: a glob of file names to move (default: everything), e.g. '*final_1015_1503*' or '*baseline2_lw8*'.
# Needs, in the environment (never in git):
#   RUNPOD_VOLUME_ID    the network volume's id (the S3 bucket)
#   RUNPOD_DATACENTER   its datacenter, e.g. EU-RO-1 (the S3 endpoint is https://s3api-<datacenter>.runpod.io)
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY   a RunPod S3 API key (Settings -> S3 API Keys)
set -euo pipefail
cd "$(dirname "$0")/../.."
what="${1:?pull or push}"
pattern="${2:-*}"
: "${RUNPOD_VOLUME_ID:?set RUNPOD_VOLUME_ID}" "${RUNPOD_DATACENTER:?set RUNPOD_DATACENTER}"
dc="$(echo "$RUNPOD_DATACENTER" | tr '[:upper:]' '[:lower:]')"
s3=(aws s3 sync --region "$RUNPOD_DATACENTER" --endpoint-url "https://s3api-$dc.runpod.io" --exclude '*' --include "$pattern")
base="s3://$RUNPOD_VOLUME_ID/fastcae-sim"
case "$what" in
  pull)
    "${s3[@]}" "$base/data/first_loop" data/first_loop
    "${s3[@]}" "$base/web/src/records" web/src/records
    ;;
  push)
    "${s3[@]}" data/first_loop "$base/data/first_loop"
    ;;
  *) echo "pull or push" >&2; exit 2 ;;
esac
