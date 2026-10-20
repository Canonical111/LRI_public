#!/bin/bash
# Wall-time continuation of one 3D array slot (FIT2D-010, FIT3D-002): runs only if the predecessor slot ended by TIMEOUT or a checkpointed stop
# (exit 75); a hard failure is left for diagnosis (exit 3). Launches array_pinned.slurm so that LRI_CPUMASK (one L=128 chain per CCX) and
# LRI_MEASUREMENTS are preserved. Env: LRI_PRED (predecessor array job id) + the array_pinned.slurm variables (exported with --export=ALL).
#SBATCH --job-name=lri3d-cont
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
  TIMEOUT:*|*:75:0) echo "$(date) predecessor $pred ended $state $code: continuing from checkpoints (mask ${LRI_CPUMASK:-none}, measurements ${LRI_MEASUREMENTS:-design})";;
  COMPLETED:0:0) echo "$(date) predecessor $pred completed: nothing to continue"; exit 0;;
  *) echo "$(date) predecessor $pred ended $state $code: hard failure, diagnose before resubmitting (runbook §5.5)"; exit 3;;
esac
exec bash "<CODE_3D>/cluster/array_pinned.slurm"
