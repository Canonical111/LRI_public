#!/bin/bash
#SBATCH --job-name=lri-precision
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --signal=B:USR1@180
#SBATCH --requeue
#SBATCH --open-mode=append
set -uo pipefail
: "${LRI_ROOT:?}" "${LRI_CAMPAIGN:?}" "${LRI_PLAN:?}" "${LRI_WORKERS:?}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$LRI_ROOT"
extra=()
if [[ -n "${LRI_MEASUREMENTS:-}" ]];then extra+=(--measurements "$LRI_MEASUREMENTS");fi
python3 run_pack.py "$LRI_CAMPAIGN" --plan "$LRI_PLAN" --slot "$SLURM_ARRAY_TASK_ID" --workers "$LRI_WORKERS" "${extra[@]}" &
child=$!
trap 'kill -USR1 "$child" 2>/dev/null || true' USR1 TERM INT
# A signal interrupts bash wait: wait again until the checkpointing child exits.
while true;do
    wait "$child";rc=$?
    if kill -0 "$child" 2>/dev/null;then continue;fi
    break
done
if [[ $rc -eq 75 && "${LRI_AUTOREQUEUE:-0}" == 1 ]];then
    scontrol requeue "${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}" || exit 75
    exit 0
fi
exit "$rc"
