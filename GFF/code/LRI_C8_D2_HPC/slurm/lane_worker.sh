#!/bin/bash
#SBATCH --job-name=c8d2-lanes
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=180G
#SBATCH --time=24:00:00
#SBATCH --output=c8d2-lanes-%j.log
# Whole-node lane worker (lane mode; submit with `slurm/submit.sh --lanes N`, which adds --exclusive and sets --mem from
# C8_LANE_MEM (180G fits symmetry Intel and AMD; 245G amdq only; 240G Expanse compute), the time, the job name and the
# tag). The node's physical cores are split into lanes (C8_LANES unset, the default: on AMD the NUMA nodes in lanes of
# at most the plan's --threads cores, 8 x 8 on symmetry and 16 x 8 on Expanse at --threads 8 (R5b, P4); on other CPUs
# one lane per socket; numa: one lane per NUMA node, 8 x 16 on Expanse; socket; or n equal parts); each lane claims job indices
# from $C8_RUN/lanes/queue.txt, heaviest first, and runs them with all its cores (tools/lanes.py). Optional: C8_LANES,
# C8_LANE_SAFETY (1.5), C8_LANE_MARGIN (300 s), C8_LANE_MAX_FAILURES (2), C8_LANE_MAX_CONSECUTIVE_FAILURES (3),
# C8_LANE_SECONDS (remaining time if squeue gives none), C8_TIME_POLICY, and the variables of slurm/run_array.sh.
# Drill mode (C8_LANE_DRILL=1, test-only plans on a shared partition): slurm/submit.sh requests -c C8_LANE_CPUS with
# --mem C8_LANE_MEM and --no-requeue, and no --exclusive; the lanes split the job's own CPU set.
# There is deliberately no #SBATCH --exclusive line: an option left off the command line cannot cancel a directive, so
# a drill would stay exclusive (CK-K01/O05). Exclusivity comes from the submitter, in normal mode only, and
# tools/slurm_submit.py reads this file's directives and refuses a submission whose effective options (directives,
# environment, command line) break the lane contract: exclusive in normal mode, never in a drill.
set -eo pipefail
if [[ -n "${C8_ENV_SETUP:-}" ]]; then [[ -r "$C8_ENV_SETUP" ]] || { echo "C8: cannot read C8_ENV_SETUP=$C8_ENV_SETUP" >&2; exit 64; }; source "$C8_ENV_SETUP"; fi
set -u
PY="${C8_PYTHON:-python3}"
"$PY" -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "C8: $PY is missing or older than Python 3.10; set C8_PYTHON or C8_ENV_SETUP" >&2; exit 64; }
: "${C8_PACKAGE:?Set C8_PACKAGE to the package directory}"
: "${C8_RUN:?Set C8_RUN to the planned campaign directory on a shared filesystem}"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
# exec: the worker IS the batch process, so a scancel, requeue or wall-limit SIGTERM reaches it; it forwards SIGTERM to
# its lanes, which stop their runs and remove their scratch, and waits at most C8_LANE_STOP_SECONDS (25 s, below
# Slurm's KillWait) before slurmstepd kills what is left (F7; tools/lanes.py).
exec "$PY" -B "$C8_PACKAGE/tools/lanes.py" worker "$C8_RUN"
