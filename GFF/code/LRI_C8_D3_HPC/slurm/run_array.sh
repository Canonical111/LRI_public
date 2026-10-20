#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
# One array element = one job index of a planned campaign (array mode, PLAN D.10). Submit only through
# `tools/slurm_submit.py submit|window|resubmit`, which sets the plan's lane width, its memory suggestion (1.5 x the
# largest est_peak_bytes + 1 GB, A-ORC-5), its suggested time, the index offset C8_INDEX_OFFSET, the throttle and the
# c8d3- name and comment. Environment: C8_PACKAGE, C8_RUN; optional C8_ENV_SETUP, C8_PYTHON, C8_STAGE=1 (run the tools
# from a node-local copy holding only the members of the index's blocks, tools/stage_runtime.py).
set -eo pipefail
source "${C8_PACKAGE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}/slurm/common.sh"
: "${C8_RUN:?Set C8_RUN to the planned campaign directory}"
: "${SLURM_ARRAY_TASK_ID:?Submit as a job array (slurm_submit.py submit)}"
[[ "${C8_INDEX_OFFSET:-0}" =~ ^[0-9]+$ ]] || { echo "C8: C8_INDEX_OFFSET must be a non-negative integer" >&2; exit 64; }
index=$(( 10#${C8_INDEX_OFFSET:-0} + SLURM_ARRAY_TASK_ID ))
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}" OMP_DYNAMIC=FALSE OMP_PLACES=cores OMP_PROC_BIND=close
package="$C8_PACKAGE"
if [[ "${C8_STAGE:-0}" == 1 ]]; then
  stage="$C8_SCRATCH/c8d3_stage_${SLURM_JOB_ID:-local}_${index}"
  "$PY" -B "$C8_PACKAGE/tools/stage_runtime.py" "$C8_RUN" "$stage" --index "$index" > /dev/null
  package="$stage"
  trap 'rm -rf "$stage"' EXIT
fi
echo "C8: index $index (offset ${C8_INDEX_OFFSET:-0} + array ${SLURM_ARRAY_TASK_ID}) on $(hostname), $OMP_NUM_THREADS threads" >&2
"$PY" -B "$package/tools/production.py" run "$C8_RUN" --index "$index" --threads "$OMP_NUM_THREADS" --scratch "$C8_SCRATCH"
