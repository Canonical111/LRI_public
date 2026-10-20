#!/bin/bash
# Whole-node lane worker (lane mode, PLAN D.9). Submit only through `tools/slurm_submit.py lanes N`, which adds
# --exclusive --nodes=1 --ntasks=1, the site options (slurm/sites/<site>/profiles.sh), the lane time (C8_LANE_TIME,
# auto by default, D.10), --no-requeue, the c8d3- name and comment and the log path. No #SBATCH line here sets a site
# value. The node's cores are split into lanes (C8_LANES: numa by default on AMD, numa:<k>, socket or n); each lane
# claims job indices of $C8_RUN/lanes/queue.txt heaviest first and runs them with its own cores (tools/lanes.py).
# Optional: C8_LANES, C8_LANE_SAFETY (1.5), C8_LANE_MARGIN (300 s), C8_LANE_MAX_FAILURES (2), C8_LANE_SECONDS,
# C8_TIME_POLICY (finite|unlimited), C8_LANE_DRILL=1 (test-only plans on shared or debug), C8_LANE_STOP_SECONDS (25).
set -eo pipefail
source "${C8_PACKAGE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}/slurm/common.sh"
: "${C8_RUN:?Set C8_RUN to the planned campaign directory}"
# exec: the worker IS the batch process, so a scancel or wall-limit SIGTERM reaches it; it forwards SIGTERM to its lanes,
# which stop their runs and remove their scratch; its whole shutdown, the killing of what is left and its own scratch
# cleanup included, ends within C8_LANE_STOP_SECONDS (25 s, below Slurm's KillWait) of the signal (F7, S2-R2-005; tools/lanes.py).
exec "$PY" -B "$C8_PACKAGE/tools/lanes.py" worker "$C8_RUN"
