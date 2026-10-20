#!/bin/bash
# Submit validation V for the frozen checkout this script lives in (review LRI-009).
# Usage (on Expanse): bash <frozen checkout>/cluster/expanse/submit_validate.sh [extra sbatch options]
# The summary is written to $LRIHT_HOME/validation/<jobid>/summary.json.
set -eo pipefail
CODE=$(cd "$(dirname "$0")/../.." && pwd)
[[ -f $CODE/GIT_SHA ]] || { echo "not a frozen checkout (no GIT_SHA): $CODE" >&2; exit 2; }
j=$(sbatch --parsable --export=ALL,CODE=$CODE "$@" "$CODE/cluster/expanse/validate.slurm")
echo "validation job $j for revision $(cat "$CODE/GIT_SHA"): summary <SCRATCH>/temp_project/lri_ht/validation/$j/summary.json"
