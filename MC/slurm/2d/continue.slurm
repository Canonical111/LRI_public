#!/bin/bash
# Wall-time continuation of one array slot (FIT2D-010): runs only if the predecessor slot ended by TIMEOUT or a checkpointed stop (exit 75);
# a hard failure (any other state/exit) is left for diagnosis (exit 3). Env: LRI_PRED (predecessor array job id) + the array.slurm variables.
#SBATCH --job-name=lri2d-cont
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --signal=B:USR1@180
#SBATCH --open-mode=append
set -uo pipefail
: "${LRI_PRED:?}" "${LRI_ROOT:?}" "${LRI_CAMPAIGN:?}" "${LRI_PLAN:?}" "${LRI_WORKERS:?}"
source /etc/profile.d/modules.sh 2>/dev/null; <LOAD_MODULES> >/dev/null 2>&1 || true  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
pred="${LRI_PRED}_${SLURM_ARRAY_TASK_ID}"; q=$(sacct -j "$pred" -X -o State,ExitCode -P -n 2>/dev/null | head -1); rc=$?
[ $rc -eq 0 ] && [ -n "$q" ] || { echo "$(date) predecessor $pred state UNKNOWN (sacct failed): not continuing"; exit 3; }
state=${q%%|*}; code=${q#*|}
case "$state:$code" in
  TIMEOUT:*|*:75:0) echo "$(date) predecessor $pred ended $state $code: continuing from checkpoints";;
  COMPLETED:0:0) echo "$(date) predecessor $pred completed: nothing to continue"; exit 0;;
  *) echo "$(date) predecessor $pred ended $state $code: hard failure, diagnose before resubmitting (runbook §5.5)"; exit 3;;
esac
exec bash "$LRI_ROOT/array.slurm"
