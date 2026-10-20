#!/bin/bash
#SBATCH --job-name=lri3d-array
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --signal=B:USR1@180
#SBATCH --requeue
#SBATCH --open-mode=append
# lri_precision_v2 array.slurm plus an optional CPU mask: run_pack.py pins worker i to the i-th CPU of its affinity mask, so
# LRI_CPUMASK="0-127:4" (one core per 4-core CCX) gives every L=128 chain its own 16 MB L3 (FIT_MODEL_3D D2; measured in a benchmark).
set -uo pipefail
: "${LRI_ROOT:?}" "${LRI_CAMPAIGN:?}" "${LRI_PLAN:?}" "${LRI_WORKERS:?}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$LRI_ROOT"
extra=()
if [[ -n "${LRI_MEASUREMENTS:-}" ]];then extra+=(--measurements "$LRI_MEASUREMENTS");fi
pin=()
if [[ -n "${LRI_CPUMASK:-}" ]];then pin=(taskset -c "$LRI_CPUMASK"); echo "$(date) cpu mask $LRI_CPUMASK -> $(taskset -c "$LRI_CPUMASK" python3 -c 'import os;print(len(os.sched_getaffinity(0)))') CPUs for $LRI_WORKERS workers";fi
"${pin[@]}" python3 run_pack.py "$LRI_CAMPAIGN" --plan "$LRI_PLAN" --slot "$SLURM_ARRAY_TASK_ID" --workers "$LRI_WORKERS" "${extra[@]}" &
child=$!
trap 'kill -USR1 "$child" 2>/dev/null || true' USR1 TERM INT
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
