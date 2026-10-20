#!/usr/bin/env bash
#SBATCH --job-name=lri-c7-d2
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --mem=4G
set -euo pipefail
: "${C7_PACKAGE:?Export the extracted package root}"
: "${C7_RUN:?Export the planned campaign directory}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
export OMP_PROC_BIND=close OMP_PLACES=cores
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
scratch="${SLURM_TMPDIR:-${TMPDIR:-/tmp}}"
index=$(( ${SLURM_ARRAY_TASK_ID:-0} + ${C7_ARRAY_OFFSET:-0} ))
if [[ "${C7_STAGE:-0}" == "1" ]]; then
    stage="${scratch}/c7d2_${SLURM_ARRAY_JOB_ID:-local}_${index}"
    python3 "$C7_PACKAGE/tools/stage_runtime.py" "$C7_RUN" "$stage" --index "$index"
    package="$stage"
else
    package="$C7_PACKAGE"
fi
python3 "$package/tools/production.py" run "$C7_RUN" --index "$index" \
    --threads "$OMP_NUM_THREADS" --scratch "$scratch"
