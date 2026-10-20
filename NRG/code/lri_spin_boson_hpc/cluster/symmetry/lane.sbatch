#!/bin/bash
# Submitted by scripts/symmetry_submit.py (all Slurm options on the command line).
# exec: Slurm's B:USR1 warning signal must reach the lane process itself.
set -euo pipefail
: "${LRI_SPIN_CODE:?}"
source "$LRI_SPIN_CODE/cluster/symmetry/env.sh"
echo "lane $SLURM_JOB_ID on $(hostname), code $(cat "$LRI_SPIN_CODE/GIT_SHA"), restart ${SLURM_RESTART_COUNT:-0}"
exec python "$LRI_SPIN_CODE/scripts/symmetry_lane.py" "$@"
